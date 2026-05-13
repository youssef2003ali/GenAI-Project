"""Unit tests for the Optimization Agent."""

import pytest
from acs_shared.schemas import AgentOutput
from acs_shared.constants import AgentName


class TestOptimizationAgent:
    """Tests for Optimization Agent."""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(self, agent_input_with_draft):
        from optimization.agent import root_agent
        output = await root_agent.execute(agent_input_with_draft)
        assert isinstance(output, AgentOutput)
        assert output.agent == AgentName.OPTIMIZATION

    @pytest.mark.asyncio
    async def test_final_content_produced(self, agent_input_with_draft):
        from optimization.agent import root_agent
        ctx = agent_input_with_draft.context
        await root_agent.execute(agent_input_with_draft)
        assert ctx.final is not None
        assert ctx.final.tone
        assert ctx.final.content
        assert ctx.final.word_count > 0
