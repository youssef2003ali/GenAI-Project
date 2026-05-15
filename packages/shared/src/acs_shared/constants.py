from enum import Enum


class Provider(str, Enum):
    OPENROUTER = 'openrouter'
    MISTRAL = 'mistral'
    GEMINI = 'gemini'
    OLLAMA = 'ollama'
    LLAMACPP = 'llamacpp'


class Model(str, Enum):
    LLAMA_3_3_70B = 'meta-llama/llama-3.3-70b-instruct:free'
    HERMES_3_405B = 'nousresearch/hermes-3-405b-instruct:free'
    GEMMA_3_27B = 'google/gemma-3-27b-it:free'
    GEMMA_3_12B = 'google/gemma-3-12b-it:free'
    GEMINI_FLASH = 'gemini-2.0-flash'
    GEMINI_FLASH_LITE = 'gemini-2.0-flash-lite'
    MISTRAL_LARGE = 'mistral-large-latest'
    MISTRAL_SMALL = 'mistral-small-latest'
    MISTRAL_NEMO = 'open-mistral-nemo'


class AgentName(str, Enum):
    RESEARCH = 'research'
    PLANNING = 'planning'
    WRITING = 'writing'
    EDITING = 'editing'
    OPTIMIZATION = 'optimization'
    ORCHESTRATOR = 'orchestrator'


class AgentStatus(str, Enum):
    SUCCESS = 'success'
    RETRY = 'retry'
    FAILED = 'failed'


AGENT_MODELS = {
    AgentName.RESEARCH: Model.MISTRAL_LARGE,
    AgentName.PLANNING: Model.MISTRAL_LARGE,
    AgentName.WRITING: Model.MISTRAL_LARGE,
    AgentName.EDITING: Model.MISTRAL_LARGE,
    AgentName.OPTIMIZATION: Model.MISTRAL_SMALL,
    AgentName.ORCHESTRATOR: Model.MISTRAL_LARGE,
}
