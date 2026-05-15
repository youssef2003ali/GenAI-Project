from pydantic import BaseModel, ConfigDict
from typing import Optional
from .constants import Provider, AgentName, AgentStatus


class AgentConfig(BaseModel):
    provider: Provider = Provider.MISTRAL
    model: str = ''
    temperature: float = 0.7
    max_tokens: int = 2048


class AgentMetadata(BaseModel):
    config: AgentConfig
    tokens_used: int = 0
    latency_ms: int = 0
    retry_count: int = 0
    error: str | None = None
    instructions: list[str] | None = None


class AgentInput(BaseModel):
    job_id: str
    topic: str
    context: 'PipelineContext'
    config: AgentConfig


class AgentOutput(BaseModel):
    job_id: str
    agent: AgentName
    result: str
    metadata: AgentMetadata
    status: AgentStatus


class ResearchOutput(BaseModel):
    summary: str
    facts: list[str]
    sources: list[str]
    raw: str


class OutlineSection(BaseModel):
    heading: str
    key_points: list[str]


class OutlineOutput(BaseModel):
    title: str
    sections: list[OutlineSection]


class DraftOutput(BaseModel):
    content: str
    word_count: int


class EditScores(BaseModel):
    coherence: int
    relevance: int
    completeness: int


class EditOutput(BaseModel):
    scores: EditScores
    average: float
    passed: bool
    retry_count: int = 0
    instructions: str | None = None


class FinalOutput(BaseModel):
    content: str
    word_count: int
    tone: str


class ContextWriteError(Exception):
    pass


class PipelineContext(BaseModel):
    research: ResearchOutput | None = None
    outline: OutlineOutput | None = None
    draft: DraftOutput | None = None
    edit: EditOutput | None = None
    final: FinalOutput | None = None
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    def set(self, key: str, value: BaseModel) -> None:
        if getattr(self, key, None) is not None:
            raise ContextWriteError(f'Context key {key} already set - append only.')
        object.__setattr__(self, key, value)

    def overwrite(self, key: str, value: BaseModel | None) -> None:
        """Replace a context key regardless of current value.

        Used by PipelineRunner during retry loops to reset agent outputs
        to ``None`` before re-executing agents.
        """
        object.__setattr__(self, key, value)


AgentInput.model_rebuild()
