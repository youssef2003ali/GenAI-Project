"""Background pipeline worker. Runs the agent pipeline and streams progress via the queue."""

import logging
import sys
import os

logger = logging.getLogger(__name__)

# Ensure agent packages are importable
_AGENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')
if _AGENTS_PATH not in sys.path:
    sys.path.insert(0, _AGENTS_PATH)

from acs_shared.schemas import ResearchOutput, OutlineSection, OutlineOutput, DraftOutput, EditOutput, EditScores, FinalOutput
from acs_shared.constants import AgentName, AgentStatus
from orchestrator.pipeline import PipelineRunner


class PipelineWorker:
    """Runs the content generation pipeline as a background task.

    Uses Phase 1 dummy agents (no API keys needed). Updates job status
    in the queue after each stage so the frontend can stream progress.
    """

    STAGE_LABELS = {
        AgentName.RESEARCH: 'research',
        AgentName.PLANNING: 'planning',
        AgentName.WRITING: 'writing',
        AgentName.EDITING: 'editing',
        AgentName.OPTIMIZATION: 'optimization',
    }

    def __init__(self, queue_service):
        self._queue = queue_service

    async def run(self, job_id: str, topic: str):
        """Execute the full pipeline and store results."""
        try:
            await self._queue.update_job(job_id, {
                'status': 'running',
                'current_agent': 'research',
                'progress': {},
            })

            # Import Phase 1 dummy agents
            from research.agent import ResearchAgent
            from planning.agent import PlanningAgent
            from writing.agent import WritingAgent
            from editing.agent import EditingAgent
            from optimization.agent import OptimizationAgent

            runner = PipelineRunner()
            runner.register_agent(AgentName.RESEARCH, ResearchAgent())
            runner.register_agent(AgentName.PLANNING, PlanningAgent())
            runner.register_agent(AgentName.WRITING, WritingAgent())
            runner.register_agent(AgentName.EDITING, EditingAgent())
            runner.register_agent(AgentName.OPTIMIZATION, OptimizationAgent())

            # Run the full pipeline
            ctx = await runner.run(job_id=job_id, topic=topic)

            # Store final results
            result_data = {
                'status': 'completed',
                'current_agent': 'optimization',
                'final_output': ctx.final.content if ctx.final else '',
                'context': ctx.model_dump() if ctx else {},
            }
            await self._queue.update_job(job_id, result_data)
            logger.info(f'Job {job_id} completed successfully')

        except Exception as e:
            logger.error(f'Job {job_id} failed: {e}')
            await self._queue.update_job(job_id, {
                'status': 'failed',
                'error': str(e),
            })
