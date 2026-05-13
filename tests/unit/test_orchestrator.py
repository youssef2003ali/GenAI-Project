"""Unit tests for the Orchestrator PipelineRunner."""

import pytest
from acs_shared.schemas import PipelineContext


class TestPipelineRunner:
    """Tests for the PipelineRunner orchestrator."""

    @pytest.mark.asyncio
    async def test_pipeline_runs_all_agents(self):
        """Pipeline should run through all agents and produce complete context."""
        from orchestrator.pipeline import PipelineRunner
        from research.agent import ResearchAgent
        from planning.agent import PlanningAgent
        from writing.agent import WritingAgent
        from editing.agent import EditingAgent
        from optimization.agent import OptimizationAgent
        from acs_shared.constants import AgentName

        runner = PipelineRunner()
        runner.register_agent(AgentName.RESEARCH, ResearchAgent())
        runner.register_agent(AgentName.PLANNING, PlanningAgent())
        runner.register_agent(AgentName.WRITING, WritingAgent())
        runner.register_agent(AgentName.EDITING, EditingAgent())
        runner.register_agent(AgentName.OPTIMIZATION, OptimizationAgent())

        context = await runner.run(job_id='test-pipeline', topic='AI Technology')
        assert isinstance(context, PipelineContext)
        assert context.research is not None
        assert context.outline is not None
        assert context.draft is not None
        assert context.edit is not None
        assert context.final is not None
