"""Health check and agent status endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get('/health')
async def health_check():
    """Basic health check for load balancers and monitoring."""
    return {'status': 'ok', 'version': '0.1.0'}


@router.get('/agents/status')
async def agents_status():
    """Return status of all 6 agents. Phase 1: all marked available."""
    agents = ['research', 'planning', 'writing', 'editing', 'optimization', 'orchestrator']
    return {'agents': {a: 'available' for a in agents}}
