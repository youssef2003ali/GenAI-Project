"""LightRAG HTTP client for backend services. Phase 1: no-op."""

from acs_shared.settings import settings


class LightRAGClient:
    """Client for interacting with the LightRAG knowledge memory service."""

    def __init__(self):
        self.url = settings.lightrag_url

    async def health_check(self) -> bool:
        """Check if LightRAG service is healthy. Phase 1: return True."""
        return True
