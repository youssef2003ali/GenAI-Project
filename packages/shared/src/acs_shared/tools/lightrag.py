"""LightRAG HTTP client tools wrapped as ADK-compatible functions.

.. note::
    Currently no-op stubs.  Wire up real ``httpx`` calls to the LightRAG
    REST API (port 9621) when the service is deployed.
"""


async def save_to_memory(text: str, metadata: dict | None = None) -> bool:
    """Save text to LightRAG knowledge graph. Phase 1: no-op."""
    return True


async def retrieve_from_memory(query: str, mode: str = 'hybrid') -> str:
    """Retrieve context from LightRAG. Phase 1: returns empty."""
    return ''
