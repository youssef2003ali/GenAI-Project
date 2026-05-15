"""Job submission, status polling, and result retrieval endpoints."""

import logging
import os
import sys
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..services.queue import get_queue
from ..routers.ws import (
    broadcast_chunk, broadcast_agent_start, broadcast_agent_done,
    broadcast_pipeline_done, broadcast_pipeline_error,
)
from acs_shared.constants import AgentName

logger = logging.getLogger(__name__)

# Ensure agent packages are importable
_AGENTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'agents',
)
if _AGENTS_PATH not in sys.path:
    sys.path.insert(0, _AGENTS_PATH)

queue_service = get_queue()

router = APIRouter()


class GenerateRequest(BaseModel):
    topic: str


class GenerateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_agent: str | None = None
    progress: dict = {}


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    final_output: str | None = None
    context: dict | None = None


@router.post('/generate', response_model=GenerateResponse)
async def generate_content(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Submit a topic for content generation. Returns a job_id for tracking."""
    job_id = str(uuid.uuid4())
    await queue_service.create_job(job_id, req.topic)

    # Launch pipeline in background
    from orchestrator.pipeline import PipelineRunner
    from research.agent import ResearchAgent
    from planning.agent import PlanningAgent
    from writing.agent import WritingAgent
    from editing.agent import EditingAgent
    from optimization.agent import OptimizationAgent

    async def _run_pipeline(job_id: str, topic: str):
        try:
            await queue_service.update_job(job_id, {
                'status': 'running',
                'current_agent': 'research',
                'progress': {},
            })

            runner = PipelineRunner()
            runner.register_agent(AgentName.RESEARCH, ResearchAgent())
            runner.register_agent(AgentName.PLANNING, PlanningAgent())
            runner.register_agent(AgentName.WRITING, WritingAgent())
            runner.register_agent(AgentName.EDITING, EditingAgent())
            runner.register_agent(AgentName.OPTIMIZATION, OptimizationAgent())

            # Chunk callback streams individual tokens to WebSocket
            async def _on_chunk(agent_name, chunk, accumulated):
                await broadcast_chunk(job_id, agent_name.value, chunk, accumulated)

            # Agent start/stop callbacks
            async def _on_agent_complete(agent_name, output_text, ctx):
                await broadcast_agent_done(job_id, agent_name.value, output_text)
                await queue_service.update_job(job_id, {
                    'status': 'running',
                    'current_agent': agent_name.value,
                    'progress': {'output': output_text},
                    'stage_output': output_text,
                })

            ctx = await runner.run(
                job_id=job_id, topic=topic,
                progress_callback=_on_agent_complete,
                chunk_callback=_on_chunk,
            )

            result_data = {
                'status': 'completed',
                'current_agent': 'optimization',
                'final_output': ctx.final.content if ctx and ctx.final else '',
                'context': ctx.model_dump() if ctx else {},
            }
            await queue_service.update_job(job_id, result_data)
            await broadcast_pipeline_done(
                job_id,
                ctx.final.content if ctx and ctx.final else '',
                ctx.model_dump() if ctx else {},
            )
            logger.info(f'Job {job_id} completed')

        except Exception as e:
            estr = str(e)
            if '429' in estr:
                msg = ('API quota exceeded. Either wait for reset, '
                       'or remove OPENROUTER_API_KEY from .env to use built-in local agents.')
            elif 'API_KEY' in estr or 'API key' in estr:
                msg = 'Invalid OPENROUTER_API_KEY. Check your .env file.'
            else:
                msg = str(e)
            logger.error(f'Job {job_id} failed: {msg}')
            await queue_service.update_job(job_id, {
                'status': 'failed',
                'error': msg,
            })
            await broadcast_pipeline_error(job_id, msg)

    background_tasks.add_task(_run_pipeline, job_id, req.topic)

    return GenerateResponse(job_id=job_id, status='queued')


@router.get('/status/{job_id}', response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll the current status of a generation job."""
    job = await queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return JobStatusResponse(
        job_id=job_id,
        status=job.get('status', 'unknown'),
        current_agent=job.get('current_agent'),
        progress=job.get('progress', {}),
    )


@router.get('/result/{job_id}', response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """Retrieve the final generated content for a completed job."""
    job = await queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    if job.get('status') not in ('completed', 'failed'):
        raise HTTPException(status_code=400, detail='Job not yet completed')
    return JobResultResponse(
        job_id=job_id,
        status=job.get('status', 'unknown'),
        final_output=job.get('final_output'),
        context=job.get('context'),
    )
