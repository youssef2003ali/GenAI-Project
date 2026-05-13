"""Redis-based job queue with in-memory fallback for Phase 1."""

import json
from typing import Any
from acs_shared.settings import settings


class QueueService:
    """Job queue backed by Redis. Falls back to in-memory dict if Redis unavailable."""

    def __init__(self):
        self._redis: Any = None
        self._jobs: dict[str, dict] = {}

    async def connect(self):
        """Connect to Redis. Phase 1: graceful fallback to in-memory."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = None  # Fall back to in-memory

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    async def create_job(self, job_id: str, topic: str) -> bool:
        job = {
            'job_id': job_id,
            'topic': topic,
            'status': 'queued',
            'current_agent': None,
            'progress': {},
            'final_output': None,
            'context': None,
        }
        if self._redis:
            await self._redis.set(f'job:{job_id}', json.dumps(job))
        else:
            self._jobs[job_id] = job
        return True

    async def update_job(self, job_id: str, updates: dict) -> bool:
        if self._redis:
            data = await self._redis.get(f'job:{job_id}')
            if data:
                job = json.loads(data)
                job.update(updates)
                await self._redis.set(f'job:{job_id}', json.dumps(job))
        elif job_id in self._jobs:
            self._jobs[job_id].update(updates)
        return True

    async def get_job(self, job_id: str) -> dict | None:
        if self._redis:
            data = await self._redis.get(f'job:{job_id}')
            return json.loads(data) if data else None
        return self._jobs.get(job_id)


_queue_service_instance: QueueService | None = None


def get_queue() -> QueueService:
    """Get or create the singleton QueueService instance."""
    global _queue_service_instance
    if _queue_service_instance is None:
        _queue_service_instance = QueueService()
    return _queue_service_instance
