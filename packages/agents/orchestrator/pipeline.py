"""Hub-spoke orchestrator. Routes tasks through agents in fixed order, handles retries.

.. deprecated::
    Use :class:`~orchestrator.adk_runner.ADKPipelineRunner` instead of this
    module's ``PipelineRunner``.  The legacy class is kept for backward
    compatibility during the transition.
"""

import asyncio
import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import (
    AgentInput,
    AgentOutput,
    AgentMetadata,
    AgentConfig,
    PipelineContext,
)
from acs_shared.constants import AgentName, Provider, AgentStatus
from acs_shared.settings import settings

from .adk_runner import ADKPipelineRunner

logger = logging.getLogger(__name__)


class PipelineRunner:
    """ADK-native pipeline runner.

    Wraps :class:`ADKPipelineRunner` and provides the same interface as the
    original custom-runner so callers in ``jobs.py`` don't need to change.
    """

    def __init__(self):
        self._agents: dict[AgentName, BaseAgent] = {}
        self._chunk_callback = None
        self._progress_callback = None

    def register_agent(self, name: AgentName, agent: BaseAgent) -> None:
        """Register an agent for pipeline execution."""
        self._agents[name] = agent

    async def run(
        self,
        job_id: str,
        topic: str,
        progress_callback=None,
        chunk_callback=None,
    ) -> PipelineContext:
        """Delegate to the ADK-native runner."""
        adk_runner = ADKPipelineRunner()
        for name, agent in self._agents.items():
            adk_runner.register_agent(name, agent)
        adk_runner.set_stream_callback(chunk_callback)
        adk_runner.set_progress_callback(progress_callback)
        return await adk_runner.run(job_id, topic)
