from .model import AgentModel
from .schemas import AgentInput, AgentOutput, AgentConfig
from .constants import AgentName, Model, AGENT_MODELS
from .settings import settings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents. Handles model init, prompt loading, and tool registration."""

    name: AgentName
    model: AgentModel

    def __init__(
        self,
        name: AgentName,
        model: AgentModel | None = None,
        config: AgentConfig | None = None,
    ):
        self.name = name
        cfg = config or AgentConfig(
            model=AGENT_MODELS.get(name, Model.LLAMA_3_3_70B).value
        )
        self.model = model or AgentModel(
            provider=cfg.provider.value,
            model=cfg.model,
            api_key=settings.openrouter_api_key,
        )
        self.config = cfg

    def load_prompt(self, agent_name: str) -> str:
        """Load prompt markdown file from prompts/{agent_name}.md."""
        prompt_path = Path(__file__).resolve().parent.parent.parent.parent.parent / 'prompts' / f'{agent_name}.md'
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        logger.warning(f'Prompt file not found: {prompt_path}')
        return f'You are the {agent_name} agent. Generate output for the given input.'

    async def execute(self, input: AgentInput) -> AgentOutput:
        """Override this in subclasses."""
        raise NotImplementedError

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
            'version': '1.0.0',
            'capabilities': {'streaming': True, 'pushNotifications': False},
            'skills': [{
                'id': f'{self.name.value}_content',
                'name': f'Generate {self.name.value} content',
                'inputModes': ['text'],
                'outputModes': ['text'],
            }],
        }
