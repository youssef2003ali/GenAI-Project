"""Unit tests for the Writing Agent."""

import pytest
from acs_shared.schemas import AgentOutput
from acs_shared.constants import AgentName


class TestWritingAgent:
    """Tests for Writing Agent."""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(self, agent_input):
        from writing.agent import root_agent
        output = await root_agent.execute(agent_input)
        assert isinstance(output, AgentOutput)
        assert output.agent == AgentName.WRITING

    @pytest.mark.asyncio
    async def test_draft_has_content(self, agent_input):
        from writing.agent import root_agent
        ctx = agent_input.context
        await root_agent.execute(agent_input)
        assert ctx.draft is not None
        assert ctx.draft.word_count >= 0
        assert ctx.draft.content
