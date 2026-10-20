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
    GEMINI_FLASH = 'gemini-3.8-flash'
    GEMINI_FLASH_LITE = 'gemini-3.5-flash-lite'
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
    AgentName.RESEARCH: Model.GEMINI_FLASH_LITE,
    AgentName.PLANNING: Model.GEMINI_FLASH_LITE,
    AgentName.WRITING: Model.GEMINI_FLASH_LITE,
    AgentName.EDITING: Model.GEMINI_FLASH_LITE,
    AgentName.OPTIMIZATION: Model.GEMINI_FLASH_LITE,
    AgentName.ORCHESTRATOR: Model.GEMINI_FLASH_LITE,
}
