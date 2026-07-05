"""Open-WebSearch MCP wrapper.

Phase 2 (real) implementation: launches the open-websearch MCP server
(https://www.npmjs.com/package/open-websearch) as a local subprocess via
`npx` and talks to it over stdio using the official MCP Python SDK.

Falls back to deterministic dummy results if the MCP server can't be
reached (no Node/npx, no network, malformed/unexpected response, timeout)
— Research must never block the whole pipeline because an external search
dependency is unavailable.
"""

import asyncio
import html
import json
import logging
import re

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False

_SEARCH_TOOL_NAME = 'search'
_MCP_TIMEOUT_SEC = 30

_STDIO_PARAMS = (
    StdioServerParameters(command='npx', args=['-y', 'open-websearch@latest']) if _HAS_MCP else None
)


def _dummy_results(query: str, num_results: int) -> list[dict]:
    """Deterministic placeholder results used when the MCP server is
    unavailable (offline dev, CI, missing Node/npx, network failure)."""
    return [
        {
            'title': f'Result {i + 1}: {query}',
            'url': f'https://example.com/result-{i + 1}',
            'description': f'Description for search result {i + 1} about {query[:30]}...',
        }
        for i in range(num_results)
    ]


_HTML_TAG_RE = re.compile(r'<[^>]+>')


def _clean_text(text: str) -> str:
    """Strip HTML tags and unescape entities from search snippets."""
    if not text:
        return ''
    return html.unescape(_HTML_TAG_RE.sub('', text)).strip()


def _normalize(item: dict) -> dict:
    """Map the MCP server's result shape onto our stable contract."""
    return {
        'title': _clean_text(item.get('title') or item.get('name') or ''),
        'url': item.get('url') or item.get('link') or '',
        'description': _clean_text(
            item.get('description') or item.get('snippet') or item.get('content') or ''
        ),
    }


def _parse_tool_result(result) -> list[dict]:
    """Extract a list of result dicts from an MCP ``CallToolResult``."""
    for block in getattr(result, 'content', []) or []:
        text = getattr(block, 'text', None)
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else data.get('results', [])
        if items:
            return [_normalize(i) for i in items if isinstance(i, dict)]
    return []


async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web for the given query via the Open-WebSearch MCP server.

    Returns a list of dicts shaped as:
        {'title': str, 'url': str, 'description': str}

    Spawns ``npx open-websearch@latest`` as a local MCP server over stdio
    for the duration of the call, then tears it down. Falls back to dummy
    placeholder results on any failure so Research never blocks the
    pipeline on an external dependency.
    """
    if not _HAS_MCP:
        logger.warning('mcp package not installed — using dummy search results')
        return _dummy_results(query, num_results)

    try:
        async with asyncio.timeout(_MCP_TIMEOUT_SEC):
            async with stdio_client(_STDIO_PARAMS) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        _SEARCH_TOOL_NAME,
                        arguments={'query': query, 'limit': num_results, 'engines': ['duckduckgo']},
                    )
        results = _parse_tool_result(result)
        if results:
            return results[:num_results]
        logger.warning(
            f"Open-WebSearch MCP returned no usable results for '{query}' "
            '— falling back to dummy results'
        )
        return _dummy_results(query, num_results)

    except Exception as exc:
        logger.warning(f'Open-WebSearch MCP failed ({exc}) — falling back to dummy results')
        return _dummy_results(query, num_results)
