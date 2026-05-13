"""Hub-spoke orchestrator. Routes tasks through agents in fixed order, handles retries."""

import asyncio
import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, AgentConfig, PipelineContext, EditOutput, EditScores
from acs_shared.constants import AgentName, Provider, AgentStatus
from acs_shared.settings import settings

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrates the full content generation pipeline.

    Routes in fixed order: Research -> Planning -> Writing -> Editing -> Optimization.
    On retry from Editing: sends back to Writing with updated context (max 3 retries).
    """

    def __init__(self):
        self._agents: dict[AgentName, BaseAgent] = {}

    def register_agent(self, name: AgentName, agent: BaseAgent) -> None:
        """Register an agent for pipeline execution."""
        self._agents[name] = agent

    async def run(self, job_id: str, topic: str, progress_callback=None) -> PipelineContext:
        """Execute the full pipeline and return the final PipelineContext."""
        context = PipelineContext()
        config = AgentConfig(
            provider=Provider.OPENROUTER,
            model=settings.orchestrator_model,
        )

        async def _report(agent_name, output_text, ctx):
            if progress_callback:
                await progress_callback(agent_name, output_text, ctx)

        # Phase 1: Route through Research -> Planning -> Writing -> Editing -> Optimization
        pipeline_order = [
            AgentName.RESEARCH,
            AgentName.PLANNING,
            AgentName.WRITING,
            AgentName.EDITING,
        ]

        for agent_name in pipeline_order:
            agent = self._agents.get(agent_name)
            if not agent:
                logger.error(f'Agent {agent_name} not registered - skipping')
                continue

            inp = AgentInput(
                job_id=job_id,
                topic=topic,
                context=context,
                config=config,
            )

            # Retry with exponential backoff on transient failures (503, 429)
            max_attempts = 3
            attempt = 0
            output = None
            while attempt < max_attempts:
                attempt += 1
                try:
                    output = await agent.execute(inp)
                    if output.status == AgentStatus.FAILED and attempt < max_attempts:
                        wait = 2 ** attempt
                        logger.warning(
                            f'Agent {agent_name} failed (attempt {attempt}/{max_attempts}): '
                            f'{output.metadata.error}. Retrying in {wait}s'
                        )
                        await asyncio.sleep(wait)
                        continue
                    break
                except Exception as e:
                    if attempt >= max_attempts:
                        output = AgentOutput(
                            job_id=job_id,
                            agent=agent_name,
                            result='',
                            metadata=AgentMetadata(config=config, tokens_used=0, latency_ms=0, error=str(e)),
                            status=AgentStatus.FAILED,
                        )
                        break
                    wait = 2 ** attempt
                    logger.warning(
                        f'Agent {agent_name} threw exception (attempt {attempt}/{max_attempts}): {e}. '
                        f'Retrying in {wait}s'
                    )
                    await asyncio.sleep(wait)

            if output.status == AgentStatus.FAILED:
                logger.warning(f'Agent {agent_name} failed after {max_attempts} attempts: {output.metadata.error}')
                continue

            # Report progress after successful agent execution
            await _report(agent_name, output.result, context)

            # Handle retry loop from Editing Agent
            if agent_name == AgentName.EDITING and output.status == AgentStatus.RETRY:
                max_retries = 3
                loop_retry_count = 0
                while output.status == AgentStatus.RETRY and loop_retry_count < max_retries:
                    loop_retry_count += 1
                    logger.info(f'Editing retry {loop_retry_count}/{max_retries}')

                    # Reset agent outputs in context so agents can write them again
                    context.overwrite('draft', None)

                    # Send back to Writing Agent with updated context
                    writing_agent = self._agents.get(AgentName.WRITING)
                    if writing_agent:
                        inp = AgentInput(
                            job_id=job_id,
                            topic=topic,
                            context=context,
                            config=config,
                        )
                        output = await writing_agent.execute(inp)
                        await _report(agent_name, output.result, context)

                    # Clear edit so editing agent can write a fresh result
                    context.overwrite('edit', None)

                    # Re-run Editing Agent
                    editing_agent = self._agents.get(AgentName.EDITING)
                    if editing_agent:
                        inp = AgentInput(
                            job_id=job_id,
                            topic=topic,
                            context=context,
                            config=config,
                        )
                        output = await editing_agent.execute(inp)
                        await _report(agent_name, output.result, context)

        # Final: Optimization Agent
        opt_agent = self._agents.get(AgentName.OPTIMIZATION)
        if opt_agent:
            inp = AgentInput(
                job_id=job_id,
                topic=topic,
                context=context,
                config=config,
            )
            output = await opt_agent.execute(inp)
            await _report(AgentName.OPTIMIZATION, output.result, context)

        return context
