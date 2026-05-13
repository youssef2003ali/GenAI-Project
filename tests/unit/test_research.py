"""Unit tests for the Research Agent."""

import pytest
from acs_shared.schemas import AgentOutput
from acs_shared.constants import AgentName, AgentStatus


class TestResearchAgent:
    """Tests for Research Agent."""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(self, agent_input):
        """Research agent should return valid AgentOutput."""
        from research.agent import root_agent
        output = await root_agent.execute(agent_input)
        assert isinstance(output, AgentOutput)
        assert output.agent == AgentName.RESEARCH
        assert output.status == AgentStatus.SUCCESS
        assert output.job_id == 'test-job-001'

    @pytest.mark.asyncio
    async def test_populates_research_context(self, agent_input):
        """Research agent should set context.research."""
        from research.agent import root_agent
        ctx = agent_input.context
        await root_agent.execute(agent_input)
        assert ctx.research is not None
        assert len(ctx.research.facts) > 0
        assert len(ctx.research.sources) > 0

    @pytest.mark.asyncio
    async def test_contains_metadata(self, agent_input):
        """Output should have filled metadata."""
        from research.agent import root_agent
        output = await root_agent.execute(agent_input)
        assert output.metadata.tokens_used >= 0
        assert output.metadata.latency_ms >= 0
