"""End-to-end integration test for the full pipeline."""

import pytest


@pytest.mark.asyncio
async def test_full_pipeline_end_to_end():
    """Full pipeline should run through all 6 agents and produce final output."""
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

    context = await runner.run(job_id='integration-test', topic='Climate Change')

    assert context.research is not None, 'Research step failed'
    assert context.outline is not None, 'Planning step failed'
    assert context.draft is not None, 'Writing step failed'
    assert context.edit is not None, 'Editing step failed'
    assert context.final is not None, 'Optimization step failed'

    # Verify data flows between agents correctly
    assert context.outline.title, 'Outline should have a title'
    assert context.draft.word_count > 0, 'Draft should have content'
    assert 0 <= context.edit.average <= 10, 'Edit scores out of range'
    assert context.final.tone, 'Final output should specify tone'
