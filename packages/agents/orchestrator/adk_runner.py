"""ADK-native pipeline orchestration using SequentialAgent + LoopAgent.

Replaces the custom ``PipelineRunner`` with Google ADK's built-in
primitives.  Each existing ``BaseAgent.execute()`` is wrapped in an
``ACSAgent`` adapter that bridges ADK's ``InvocationContext`` with our
``PipelineContext``.
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from google.adk.agents import Agent as ADKAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.events.event import Event, EventActions
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from acs_shared.base_agent import BaseAgent as ACSBaseAgent
from acs_shared.schemas import (
    AgentInput,
    AgentConfig,
    AgentOutput,
    PipelineContext,
)
from acs_shared.constants import Provider, AgentName, AgentStatus, AGENT_MODELS
from acs_shared.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK Agent that wraps an existing ACS BaseAgent
# ---------------------------------------------------------------------------


class ACSAgent(ADKAgent):
    """Wraps an ACS ``BaseAgent`` so it can run inside an ADK pipeline.

    The wrapped agent's ``execute()`` method is called with an
    ``AgentInput`` reconstructed from ADK's session state.  Results are
    written back into ``session.state["pipeline_context"]`` so the next
    agent in the chain can see them.
    """

    def __init__(self, *, acs_agent: ACSBaseAgent, **kwargs):
        super().__init__(
            name=acs_agent.name.value,
            instruction='',  # not needed — our agent loads its own prompt
            **kwargs,
        )
        self._acs = acs_agent
        # Wire a chunk callback bridge for streaming (see _run_async_impl)
        self._stream_callback: callable | None = None

    # Map AgentName → PipelineContext key for retry clearing
    _CONTEXT_KEY: dict[AgentName, str] = {
        AgentName.RESEARCH: 'research',
        AgentName.PLANNING: 'outline',
        AgentName.WRITING: 'draft',
        AgentName.EDITING: 'edit',
        AgentName.OPTIMIZATION: 'final',
    }

    async def _run_async_impl(  # type: ignore[override]
        self, ctx,
    ) -> AsyncGenerator[Event, None]:
        # 1. Reconstruct our PipelineContext from ADK session state
        pc_data = ctx.session.state.get('pipeline_context', {})
        pipeline_ctx = (
            PipelineContext(**pc_data) if pc_data else PipelineContext()
        )

        # 2. Clear the agent's output key if already set (needed when a
        #    LoopAgent retries Writing after a failed Edit).
        ck = self._CONTEXT_KEY.get(self._acs.name)
        if ck and getattr(pipeline_ctx, ck, None) is not None:
            pipeline_ctx.overwrite(ck, None)

        # 3. Build AgentInput
        agent_input = AgentInput(
            job_id=ctx.session.state.get('job_id', 'unknown'),
            topic=ctx.session.state.get('topic', ''),
            context=pipeline_ctx,
            config=AgentConfig(
                provider=Provider.MISTRAL,
                model=(
                    getattr(settings, f'{self._acs.name.value}_model', None)
                    or (AGENT_MODELS.get(self._acs.name).value if AGENT_MODELS.get(self._acs.name) else None)
                    or settings.mistral_model
                ),
            ),
        )

        # Wire streaming so BaseAgent._chunk_callback fires
        if self._stream_callback:
            self._acs._chunk_callback = self._stream_callback
        else:
            self._acs._chunk_callback = None

        # 4. Run the agent
        output = await self._acs.run(agent_input)

        # 4. Build state delta so the Runner merges it into session state
        state_delta = {
            'pipeline_context': pipeline_ctx.model_dump(),
            self._acs.name.value: output.result,
        }

        # 5. Yield an ADK Event so SequentialAgent / LoopAgent can observe it
        event = Event(
            author=self._acs.name.value,
            actions=EventActions(
                escalate=False,
                state_delta=state_delta,
                artifact_delta={},
                requested_auth_configs={},
                requested_tool_confirmations={},
            ),
            timestamp=time.time(),
            content=types.Content(
                role='model',
                parts=[types.Part(text=output.result or '')],
            ),
        )

        # Signal LoopAgent to exit if editing passes
        if (
            self._acs.name == AgentName.EDITING
            and output.status == AgentStatus.SUCCESS
        ):
            event.actions.escalate = True

        yield event


# ---------------------------------------------------------------------------
# Pipeline builder & runner
# ---------------------------------------------------------------------------


class ADKPipelineRunner:
    """Builds and executes the content pipeline with ADK primitives.

    Pipeline topology::

        SequentialAgent
        ├── ResearchAgent
        ├── PlanningAgent
        ├── EditRetryLoop (LoopAgent, max_iterations=3)
        │   ├── WritingAgent
        │   └── EditingAgent   ← escalates when PASS
        └── OptimizationAgent
    """

    def __init__(self):
        self._agents: dict[AgentName, ACSBaseAgent] = {}
        self._chunk_callback = None
        self._progress_callback = None

    def register_agent(self, name: AgentName, agent: ACSBaseAgent) -> None:
        self._agents[name] = agent

    def set_stream_callback(self, cb):
        """Set a callback ``callable(agent_name, chunk, accumulated)``."""
        self._chunk_callback = cb

    def set_progress_callback(self, cb):
        """Set a callback ``callable(agent_name, output_text, ctx)``."""
        self._progress_callback = cb

    # ------------------------------------------------------------------
    # Build the agent tree
    # ------------------------------------------------------------------

    def _build_pipeline(self) -> SequentialAgent:
        def _wrap(name: AgentName) -> ACSAgent:
            agent = self._agents.get(name)
            if not agent:
                raise ValueError(f'Agent {name.value} not registered')
            wrapped = ACSAgent(acs_agent=agent)
            if self._chunk_callback:
                cb = self._chunk_callback
                wrapped._stream_callback = (
                    lambda chunk, acc, _n=name: cb(
                        _n, chunk, acc
                    )
                )
            return wrapped

        research = _wrap(AgentName.RESEARCH)
        planning = _wrap(AgentName.PLANNING)
        writing = _wrap(AgentName.WRITING)
        editing = _wrap(AgentName.EDITING)
        optimization = _wrap(AgentName.OPTIMIZATION)

        # Edit retry loop: [Writing → Editing], repeat until editing
        # signals ``escalate=True`` or max_iterations reached.
        edit_loop = LoopAgent(
            name='EditRetryLoop',
            sub_agents=[writing, editing],
            max_iterations=3,
        )

        return SequentialAgent(
            name='ContentPipeline',
            sub_agents=[research, planning, edit_loop, optimization],
        )

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def run(
        self, job_id: str, topic: str,
    ) -> PipelineContext:
        """Run the pipeline and return the final ``PipelineContext``."""
        pipeline = self._build_pipeline()
        session_service = InMemorySessionService()

        session = await session_service.create_session(
            app_name='acs',
            user_id='default',
            session_id=job_id,
        )
        session.state['job_id'] = job_id
        session.state['topic'] = topic
        session.state['pipeline_context'] = {}

        runner = Runner(
            agent=pipeline,
            app_name='acs',
            session_service=session_service,
        )

        content = types.Content(
            role='user',
            parts=[types.Part(text=f'Generate content about: {topic}')],
        )

        # Consume all events (needed for the pipeline to complete)
        async for _event in runner.run_async(
            user_id='default',
            session_id=job_id,
            new_message=content,
        ):
            # Convert ADK's string author back to AgentName enum for callbacks
            agent_name_str = _event.author
            try:
                agent_name = AgentName(agent_name_str)
            except ValueError:
                agent_name = agent_name_str

            # Fire progress callback on agent completion
            if (
                _event.content
                and _event.content.parts
                and self._progress_callback
            ):
                await self._progress_callback(
                    agent_name,
                    _event.content.parts[0].text or '',
                    session.state.get('pipeline_context', {}),
                )

        # Re-fetch session (ADK returns a new object each call)
        final_session = await session_service.get_session(
            app_name='acs',
            user_id='default',
            session_id=job_id,
        )
        pc_data = (
            final_session.state.get('pipeline_context', {})
            if final_session else {}
        )
        if pc_data:
            return PipelineContext(**pc_data)
        return PipelineContext()
