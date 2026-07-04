"""Scrapling MCP wrapper.

Phase 2 (real) implementation: launches the Scrapling MCP server
(https://scrapling.readthedocs.io/en/latest/ai/mcp-server.html) as a
local subprocess over stdio using the official MCP Python SDK, and
extracts clean page content from a URL.

Escalation strategy (per Scrapling's own guidance): try the fast `get`
tool (plain HTTP, no JS) first; only escalate to the heavier, browser-
based `fetch` tool if `get` returns nothing usable.

Falls back to deterministic dummy content if the MCP server can't be
reached (Scrapling not installed, browser deps missing, no network,
timeout) — Research must never block the pipeline because an external
scraping dependency is unavailable.
"""

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False

_MCP_TIMEOUT_SEC = 40
_MAX_CONTENT_CHARS = 5000

_STDIO_PARAMS = StdioServerParameters(command='scrapling', args=['mcp']) if _HAS_MCP else None

_COMMON_ARGS = {
    'extraction_type': 'markdown',
    'main_content_only': True,
}


def _dummy_content(url: str) -> str:
    """Deterministic placeholder content used when the MCP server is
    unavailable (offline dev, CI, Scrapling/browser deps missing)."""
    return (
        f'Extracted content from {url}: This is simulated extracted '
        f'content for Phase 1 skeleton testing. In Phase 2, Scrapling '
        f'will extract real content from the page.'
    )


def _parse_tool_result(result) -> str:
    """Extract page text/markdown from an MCP ``CallToolResult``.

    Scrapling's tools return a ``ResponseModel`` with fields
    ``status`` (int), ``content`` (list[str] or str), ``url`` (str),
    serialized as JSON text content.
    """
    for block in getattr(result, 'content', []) or []:
        text = getattr(block, 'text', None)
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            # Not JSON — treat the raw text itself as the content.
            return text.strip()

        content = data.get('content', '')
        if isinstance(content, list):
            content = '\n'.join(str(c) for c in content)
        status = data.get('status')
        if content and (status is None or 200 <= int(status) < 400):
            return str(content).strip()
    return ''


async def _call_tool(session, tool_name: str, url: str) -> str:
    result = await session.call_tool(
        tool_name,
        arguments={'url': url, **_COMMON_ARGS},
    )
    return _parse_tool_result(result)


async def scrape_content(url: str) -> str:
    """Extract clean content from a URL via the Scrapling MCP server.

    Tries the fast `get` tool first (plain HTTP, no JS rendering); if
    that yields nothing usable, escalates to the browser-based `fetch`
    tool. Falls back to dummy placeholder text on any failure so
    Research never blocks the pipeline on an external dependency.
    """
    if not _HAS_MCP:
        logger.warning('mcp package not installed — using dummy scrape content')
        return _dummy_content(url)

    try:
        async with asyncio.timeout(_MCP_TIMEOUT_SEC):
            async with stdio_client(_STDIO_PARAMS) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    content = await _call_tool(session, 'get', url)
                    if not content:
                        logger.info(f"'get' returned nothing for {url}, escalating to 'fetch'")
                        content = await _call_tool(session, 'fetch', url)

        if content:
            return content[:_MAX_CONTENT_CHARS]
        logger.warning(f'Scrapling returned no content for {url} — using dummy content')
        return _dummy_content(url)

    except Exception as exc:
        logger.warning(f'Scrapling MCP failed for {url} ({exc}) — falling back to dummy content')
        return _dummy_content(url)
