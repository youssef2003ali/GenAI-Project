"""Unit tests for the Planning Agent."""

import pytest
from acs_shared.schemas import AgentOutput
from acs_shared.constants import AgentName


class TestPlanningAgent:
    """Tests for Planning Agent."""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(self, agent_input):
        from planning.agent import root_agent
        output = await root_agent.execute(agent_input)
        assert isinstance(output, AgentOutput)
        assert output.agent == AgentName.PLANNING

    @pytest.mark.asyncio
    async def test_outline_has_sections(self, agent_input):
        from planning.agent import root_agent
        ctx = agent_input.context
        await root_agent.execute(agent_input)
        assert ctx.outline is not None
        # Phase 1: dummy output produces 1 fallback section
        # Phase 2: real LLM produces 3-7 sections per architecture spec
        assert len(ctx.outline.sections) >= 1

    @pytest.mark.asyncio
    async def test_each_section_has_heading_and_key_points(self, agent_input):
        from planning.agent import root_agent
        ctx = agent_input.context
        await root_agent.execute(agent_input)
        for section in ctx.outline.sections:
            assert section.heading
            assert len(section.key_points) > 0
