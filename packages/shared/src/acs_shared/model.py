"""Provider-agnostic model interface via LiteLLM.

All LLM calls route through LiteLLM_ which supports Mistral, Gemini,
OpenRouter, Ollama, and 100+ providers through a unified API.

    .. _LiteLLM: https://docs.litellm.ai
"""

import asyncio
import os
import time
from .settings import settings

# Shorten LiteLLM's generous default timeouts so the dummy
# fallback kicks in quickly during development / testing.
_REQUEST_TIMEOUT_SEC = 120

# Disable LiteLLM's internal retries — we handle retry at the pipeline level.
try:
    import litellm as _litellm
    _litellm.num_retries = 0
    _litellm.request_timeout = _REQUEST_TIMEOUT_SEC
except ImportError:
    pass


class AgentModel:
    """Provider-agnostic model interface backed by LiteLLM.

    Keeps the same public contract (``generate``, ``generate_stream``,
    ``generate_with_metrics``) so no agent code needs to change.
    """

    def __init__(self, provider: str, model: str, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key or ''
        self._ensure_env()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_env(self) -> None:
        """Set the environment variable LiteLLM uses to find the API key."""
        key_var = {
            'mistral': 'MISTRAL_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'ollama': '',
            'llamacpp': '',
        }.get(self.provider, '')

        if key_var and not os.environ.get(key_var):
            raw = getattr(settings, key_var.lower(), '') or self.api_key
            if raw:
                os.environ[key_var] = raw

    def _litellm_model(self) -> str:
        """Map internal (provider, model) → LiteLLM model string."""
        prefix = {
            'mistral': 'mistral',
            'openrouter': 'openrouter',
            'gemini': 'gemini',
            'ollama': 'ollama_chat',
            'llamacpp': 'openai',
        }.get(self.provider, 'openai')
        return f'{prefix}/{self.model}'

    # ------------------------------------------------------------------
    # Public generation API  (same contract as before)
    # ------------------------------------------------------------------

    async def generate(self, prompt: str) -> str:
        """Generate text through LiteLLM, falling back to dummy on failure."""
        # Lazy-import so missing litellm doesn't crash imports
        import litellm

        try:
            response = await litellm.acompletion(
                model=self._litellm_model(),
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7,
                max_tokens=2048,
                timeout=_REQUEST_TIMEOUT_SEC,
                num_retries=0,
            )
            return response.choices[0].message.content or ''
        except Exception:
            # Graceful fallback — useful during development / demo
            await asyncio.sleep(0.1)
            return (
                f'[Dummy from {self.provider}/{self.model}]: '
                f'Generated for: {prompt[:80]}…'
            )

    async def generate_stream(self, prompt: str):
        """Stream from provider through LiteLLM.

        Yields ``(content_chunk, full_text_so_far)`` tuples, same as
        the original ``_generate_mistral_stream``.
        """
        import litellm

        try:
            response = await litellm.acompletion(
                model=self._litellm_model(),
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7,
                max_tokens=2048,
                stream=True,
                timeout=_REQUEST_TIMEOUT_SEC,
                num_retries=0,
            )
            accumulated = ''
            async for chunk in response:
                delta = (
                    chunk.choices[0].delta.content
                    if chunk.choices and chunk.choices[0].delta
                    else ''
                )
                if delta:
                    accumulated += delta
                    yield (delta, accumulated)
        except Exception:
            full = await self.generate(prompt)
            yield (full, full)

    async def generate_with_metrics(
        self, prompt: str,
    ) -> tuple[str, int, int]:
        """Generate and return ``(text, tokens_used, latency_ms)``."""
        start = time.time()
        text = await self.generate(prompt)
        latency = int((time.time() - start) * 1000)
        tokens = len(text.split())
        return text, tokens, latency
