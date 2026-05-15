import time
from .model import AgentModel
from .schemas import AgentInput, AgentOutput, AgentConfig
from .constants import AgentName, Model, AGENT_MODELS, AgentStatus
from .settings import settings
from pathlib import Path
import logging

# TODO Phase 2: Replace logging with loguru for structured logging
logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents. Handles model init, prompt loading, and tool registration."""

    name: AgentName
    model: AgentModel
    _metrics: dict = {'requests_total': 0, 'tokens_total': 0, 'failures_total': 0}
    _chunk_callback: callable = None

    def __init__(
        self,
        name: AgentName,
        model: AgentModel | None = None,
        config: AgentConfig | None = None,
        url: str = '',
    ):
        self.name = name
        self.url = url
        cfg = config or AgentConfig(
            model=AGENT_MODELS.get(name, Model.LLAMA_3_3_70B).value
        )
        self.model = model or AgentModel(
            provider=cfg.provider.value,
            model=cfg.model,
            api_key=self._resolve_api_key(cfg.provider.value),
        )

    def _resolve_api_key(self, provider: str) -> str:
        """Return the correct API key for the given provider."""
        if provider == 'gemini':
            return settings.gemini_api_key
        if provider == 'mistral':
            return settings.mistral_api_key
        return settings.openrouter_api_key
        self.config = cfg

    def load_prompt(self, agent_name: str) -> str:
        """Load prompt markdown file from prompts/{agent_name}.md."""
        prompt_path = Path(__file__).resolve().parent.parent.parent.parent.parent / 'prompts' / f'{agent_name}.md'
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        logger.warning(f'Prompt file not found: {prompt_path}')
        return f'You are the {agent_name} agent. Generate output for the given input.'

    async def generate_text(self, prompt: str) -> tuple[str, int, int]:
        """Generate text. Streams via chunk_callback if set."""
        if self._chunk_callback:
            return await self.generate_text_stream(prompt, self._chunk_callback)
        return await self.model.generate_with_metrics(prompt)

    async def generate_text_stream(self, prompt: str, chunk_callback=None):
        """Stream generate text. Yields chunks and calls chunk_callback if provided.
        
        Returns (full_text, tokens, latency_ms) like generate_text().
        """
        start = time.time()
        full_text = ''
        async for chunk, accumulated in self.model.generate_stream(prompt):
            full_text = accumulated
            if chunk_callback:
                await chunk_callback(chunk, accumulated)
        latency = int((time.time() - start) * 1000)
        tokens = len(full_text.split())
        return full_text, tokens, latency

    async def execute(self, input: AgentInput) -> AgentOutput:
        """Override this in subclasses."""
        raise NotImplementedError

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the agent and log results to MLflow."""
        output = await self.execute(input)
        await self._log_to_mlflow(input, output)
        self._metrics['requests_total'] += 1
        self._metrics['tokens_total'] += output.metadata.tokens_used
        if output.status in (AgentStatus.FAILED, AgentStatus.RETRY):
            self._metrics['failures_total'] += 1
        return output

    async def _log_to_mlflow(self, input: AgentInput, output: AgentOutput) -> None:
        """Log agent run to MLflow. Fails silently if MLflow is not installed."""
        try:
            import mlflow  # noqa: F811
            with mlflow.start_run(run_name=f'{self.name.value}-{input.job_id}'):
                mlflow.log_params({
                    'model': self.model.model,
                    'provider': self.model.provider,
                })
                mlflow.log_metrics({
                    'tokens_used': output.metadata.tokens_used,
                    'latency_ms': output.metadata.latency_ms,
                    'retry_count': output.metadata.retry_count,
                })
                mlflow.set_tags({
                    'status': output.status.value if hasattr(output.status, 'value') else output.status,
                    'topic': input.topic,
                })
        except Exception:
            logger.debug('MLflow not available - skipping telemetry')

    def _default_port(self) -> int:
        """Return default port based on agent name."""
        port_map = {
            'research': 8100,
            'planning': 8101,
            'writing': 8102,
            'editing': 8103,
            'optimization': 8104,
            'orchestrator': 8105,
        }
        return port_map.get(self.name.value, 8100)

    # In Phase 2, these become ADK FunctionTools registered automatically
    async def save_to_memory(self, text: str, metadata: dict | None = None) -> bool:
        """Save knowledge to LightRAG. Phase 1: no-op that returns True."""
        return True

    async def retrieve_from_memory(self, query: str, mode: str = 'hybrid') -> str:
        """Retrieve context from LightRAG. Phase 1: returns empty string."""
        return ''

    @property
    def card(self) -> dict:
        """Agent Card for A2A discovery."""
        return {
            'name': self.name.value.title() + ' Agent',
            'description': f'{self.name.value.title()} agent for content generation',
            'url': self.url or f'http://localhost:{self._default_port()}',
            'version': '1.0.0',
            'capabilities': {'streaming': True, 'pushNotifications': False},
            'skills': [{
                'id': f'{self.name.value}_content',
                'name': f'Generate {self.name.value} content',
                'inputModes': ['text'],
                'outputModes': ['text'],
            }],
        }

    @property
    def metrics(self) -> dict:
        """Return current Prometheus metrics counters."""
        return dict(self._metrics)

    def get_metrics_text(self) -> str:
        """Return metrics in Prometheus exposition format."""
        name = self.name.value
        success = self._metrics['requests_total'] - self._metrics['failures_total']
        return (
            '# HELP agent_requests_total Total requests\n'
            '# TYPE agent_requests_total counter\n'
            f'agent_requests_total{{agent="{name}",status="success"}} {success}\n'
            f'agent_requests_total{{agent="{name}",status="failure"}} {self._metrics["failures_total"]}\n'
            '# HELP agent_tokens_total Total tokens used\n'
            '# TYPE agent_tokens_total counter\n'
            f'agent_tokens_total{{agent="{name}"}} {self._metrics["tokens_total"]}\n'
        )
