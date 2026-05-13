import asyncio
import time
from .settings import settings


class AgentModel:
    """Provider-agnostic model interface. Phase 1: dummy implementation."""

    def __init__(self, provider: str, model: str, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key or ''

    async def generate(self, prompt: str) -> str:
        """Generate text. Phase 1: returns dummy response for skeleton testing."""
        await asyncio.sleep(0.1)
        return f'[Dummy from {self.provider}/{self.model}]: Generated for: {prompt[:80]}...'

    async def generate_with_metrics(self, prompt: str) -> tuple[str, int, int]:
        """Generate and return (text, tokens_used, latency_ms)."""
        start = time.time()
        text = await self.generate(prompt)
        latency = int((time.time() - start) * 1000)
        tokens = len(text.split())
        return text, tokens, latency
