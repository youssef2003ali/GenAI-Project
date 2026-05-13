"""Open-WebSearch MCP wrapper. Phase 1: dummy implementation."""


async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web for the given query. Returns structured results."""
    return [
        {
            'title': f'Result {i+1}: {query}',
            'url': f'https://example.com/result-{i+1}',
            'description': f'Description for search result {i+1} about {query[:30]}...',
        }
        for i in range(num_results)
    ]
