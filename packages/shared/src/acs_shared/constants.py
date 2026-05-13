from enum import Enum


class Provider(str, Enum):
    OPENROUTER = 'openrouter'
    OLLAMA = 'ollama'
    LLAMACPP = 'llamacpp'


class Model(str, Enum):
    LLAMA_3_3_70B = 'meta-llama/llama-3.3-70b-instruct:free'
    HERMES_3_405B = 'nousresearch/hermes-3-405b-instruct:free'
    GEMMA_3_27B = 'google/gemma-3-27b-it:free'
    GEMMA_3_12B = 'google/gemma-3-12b-it:free'


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
    AgentName.RESEARCH: Model.LLAMA_3_3_70B,
    AgentName.PLANNING: Model.HERMES_3_405B,
    AgentName.WRITING: Model.GEMMA_3_27B,
    AgentName.EDITING: Model.GEMMA_3_27B,
    AgentName.OPTIMIZATION: Model.GEMMA_3_12B,
    AgentName.ORCHESTRATOR: Model.HERMES_3_405B,
}
