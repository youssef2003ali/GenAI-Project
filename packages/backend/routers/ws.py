"""WebSocket endpoint for real-time pipeline progress streaming."""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.queue import get_queue

queue_service = get_queue()

router = APIRouter()


@router.websocket('/ws/{job_id}')
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """Stream real-time agent transitions for a job via WebSocket."""
    await websocket.accept()
    try:
        while True:
            job = await queue_service.get_job(job_id)
            if job:
                await websocket.send_json({
                    'job_id': job_id,
                    'status': job.get('status'),
                    'current_agent': job.get('current_agent'),
                    'progress': job.get('progress', {}),
                })
                if job.get('status') in ('completed', 'failed'):
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
