"""Unit tests for the Editing Agent."""

import pytest
from acs_shared.schemas import AgentOutput
from acs_shared.constants import AgentName


class TestEditingAgent:
    """Tests for Editing Agent."""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(self, agent_input):
        from editing.agent import root_agent
        output = await root_agent.execute(agent_input)
        assert isinstance(output, AgentOutput)
        assert output.agent == AgentName.EDITING

    @pytest.mark.asyncio
    async def test_scores_in_valid_range(self, agent_input):
        from editing.agent import root_agent
        ctx = agent_input.context
        await root_agent.execute(agent_input)
        assert ctx.edit is not None
        s = ctx.edit.scores
        assert 0 <= s.coherence <= 10
        assert 0 <= s.relevance <= 10
        assert 0 <= s.completeness <= 10
        assert 0 <= ctx.edit.average <= 10
