"""FastAPI application entrypoint. Phase 1: in-memory queue, no real DB."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health, jobs, ws
from .services.queue import get_queue
from .db.models import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB (no-op Phase 1), connect Redis (graceful fallback)."""
    await init_db()
    qs = get_queue()
    await qs.connect()
    logger.info('Backend started')
    yield
    await qs.disconnect()
    logger.info('Backend shut down')


app = FastAPI(
    title='Agentic Content System',
    version='0.1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(ws.router)
