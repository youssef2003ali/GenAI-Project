"""Job submission, status polling, and result retrieval endpoints."""

import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..services.queue import get_queue

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
    from ..services.worker import PipelineWorker
    worker = PipelineWorker(queue_service)
    background_tasks.add_task(worker.run, job_id, req.topic)

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
