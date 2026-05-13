"""Background pipeline worker. Runs ADK + Gemini when API key available,
falls back to Phase 1 dummy agents. Streams progress via the queue."""

import logging
import sys
import os

logger = logging.getLogger(__name__)

_AGENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')
if _AGENTS_PATH not in sys.path:
    sys.path.insert(0, _AGENTS_PATH)

from acs_shared.constants import AgentName, AgentStatus


class PipelineWorker:
    """Runs the content generation pipeline as a background task.

    Uses ADK + Gemini 2.5 Flash when GEMINI_API_KEY is set in .env.
    Falls back to Phase 1 dummy agents (hardcoded data, no API key needed).
    """

    def __init__(self, queue_service):
        self._queue = queue_service

    async def run(self, job_id: str, topic: str):
        try:
            await self._queue.update_job(job_id, {
                'status': 'running',
                'current_agent': 'research',
                'progress': {},
            })

            # Try ADK + Gemini first
            ctx = None
            from .adk_pipeline import create_adk_pipeline_runner
            runner = await create_adk_pipeline_runner()

            if runner:
                logger.info(f'Job {job_id}: using ADK + Gemini pipeline')
                ctx = await runner.run(job_id=job_id, topic=topic)
            else:
                # Fall back to Phase 1 dummy agents
                logger.info(f'Job {job_id}: using Phase 1 dummy agents')
                from research.agent import ResearchAgent
                from planning.agent import PlanningAgent
                from writing.agent import WritingAgent
                from editing.agent import EditingAgent
                from optimization.agent import OptimizationAgent
                from orchestrator.pipeline import PipelineRunner

                runner = PipelineRunner()
                runner.register_agent(AgentName.RESEARCH, ResearchAgent())
                runner.register_agent(AgentName.PLANNING, PlanningAgent())
                runner.register_agent(AgentName.WRITING, WritingAgent())
                runner.register_agent(AgentName.EDITING, EditingAgent())
                runner.register_agent(AgentName.OPTIMIZATION, OptimizationAgent())
                ctx = await runner.run(job_id=job_id, topic=topic)

            # Store results
            result_data = {
                'status': 'completed',
                'current_agent': 'optimization',
                'final_output': ctx.final.content if ctx and ctx.final else '',
                'context': ctx.model_dump() if ctx else {},
            }
            await self._queue.update_job(job_id, result_data)
            logger.info(f'Job {job_id} completed')

        except Exception as e:
            estr = str(e)
            # Provide a clear message for common errors
            if '429' in estr:
                msg = ('Gemini API quota exceeded. Either wait for reset, '
                       'or remove GEMINI_API_KEY from .env to use built-in dummy agents.')
            elif 'API_KEY' in estr or 'API key' in estr:
                msg = 'Invalid GEMINI_API_KEY. Check your .env file.'
            else:
                msg = str(e)
            logger.error(f'Job {job_id} failed: {msg}')
            await self._queue.update_job(job_id, {
                'status': 'failed',
                'error': msg,
            })
