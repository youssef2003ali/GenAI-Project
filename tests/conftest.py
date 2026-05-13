"""Shared pytest fixtures for all agent tests."""

import pytest
from acs_shared.schemas import (
    AgentInput, AgentOutput, AgentConfig, AgentMetadata,
    PipelineContext, ResearchOutput, OutlineOutput, OutlineSection,
    DraftOutput, EditOutput, EditScores, FinalOutput,
)
from acs_shared.constants import Provider, AgentName, AgentStatus
from acs_shared.base_agent import BaseAgent


@pytest.fixture
def pipeline_context():
    """Return an empty PipelineContext.

    Each agent test starts from scratch and lets the agent set its own stage
    output. For tests that need predecessor data (e.g. Optimization needs
    Draft), use the specific stage fixtures below.
    """
    return PipelineContext()


@pytest.fixture
def context_with_draft():
    """PipelineContext with research + outline + draft pre-populated.

    Used by Optimization tests which need input.context.draft to be set.
    """
    ctx = PipelineContext()
    ctx.set('research', ResearchOutput(
        summary='Test research summary',
        facts=['Fact 1', 'Fact 2'],
        sources=['https://example.com'],
        raw='Raw content here',
    ))
    ctx.set('outline', OutlineOutput(
        title='Test Title',
        sections=[
            OutlineSection(heading='Intro', key_points=['Point 1']),
            OutlineSection(heading='Body', key_points=['Point 2']),
            OutlineSection(heading='Conclusion', key_points=['Point 3']),
        ],
    ))
    ctx.set('draft', DraftOutput(
        content='This is a test draft content with enough words to simulate a real output. ' * 10,
        word_count=100,
    ))
    return ctx


@pytest.fixture
def agent_input_with_draft(context_with_draft):
    """AgentInput with research + outline + draft pre-populated."""
    return AgentInput(
        job_id='test-job-001',
        topic='Artificial Intelligence',
        context=context_with_draft,
        config=AgentConfig(provider=Provider.OPENROUTER, model='test-model'),
    )


@pytest.fixture
def agent_input(pipeline_context):
    """Standard AgentInput fixture for tests."""
    return AgentInput(
        job_id='test-job-001',
        topic='Artificial Intelligence',
        context=pipeline_context,
        config=AgentConfig(provider=Provider.OPENROUTER, model='test-model'),
    )


class DummyAgent(BaseAgent):
    """Minimal agent implementation for testing BaseAgent functionality."""

    def __init__(self):
        super().__init__(name=AgentName.RESEARCH)

    async def execute(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.RESEARCH,
            result='dummy result',
            metadata=AgentMetadata(config=input.config, tokens_used=10, latency_ms=10),
            status=AgentStatus.SUCCESS,
        )
