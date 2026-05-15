"""WebSocket endpoint for real-time pipeline progress streaming.

Uses push-based architecture: pipeline sends chunks directly to active
WebSocket connections via the broadcast functions below. No polling needed.
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Registry of active WebSocket connections per job_id
_active_connections: dict[str, set[WebSocket]] = {}


async def send_to_job(job_id: str, data: dict):
    """Send a JSON message to all WebSocket listeners for a job."""
    sockets = _active_connections.get(job_id, set())
    dead = set()
    for ws in sockets:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    sockets -= dead


async def broadcast_chunk(job_id: str, agent: str, chunk: str, accumulated: str):
    """Stream a content chunk from an agent to the frontend."""
    await send_to_job(job_id, {
        'type': 'chunk',
        'agent': agent,
        'content': chunk,
    })


async def broadcast_agent_start(job_id: str, agent: str):
    """Notify frontend that an agent has started."""
    await send_to_job(job_id, {
        'type': 'agent_start',
        'agent': agent,
    })


async def broadcast_agent_done(job_id: str, agent: str, full_output: str):
    """Notify frontend that an agent completed."""
    await send_to_job(job_id, {
        'type': 'agent_done',
        'agent': agent,
        'output': full_output,
    })


async def broadcast_pipeline_done(job_id: str, final_output: str, context: dict):
    """Notify frontend that the full pipeline completed."""
    await send_to_job(job_id, {
        'type': 'pipeline_done',
        'final_output': final_output,
        'context': context,
    })


async def broadcast_pipeline_error(job_id: str, error: str):
    """Notify frontend of a pipeline failure."""
    await send_to_job(job_id, {
        'type': 'pipeline_error',
        'error': error,
    })


@router.websocket('/ws/{job_id}')
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """Stream real-time agent transitions for a job via WebSocket push."""
    await websocket.accept()

    if job_id not in _active_connections:
        _active_connections[job_id] = set()
    _active_connections[job_id].add(websocket)

    try:
        # Keep connection alive until client disconnects
        while True:
            received = await websocket.receive_text()
            # Client can send ping to keep alive
            if received == 'ping':
                await websocket.send_json({'type': 'pong'})
    except WebSocketDisconnect:
        pass
    finally:
        sockets = _active_connections.get(job_id, set())
        sockets.discard(websocket)
        if not sockets:
            _active_connections.pop(job_id, None)
