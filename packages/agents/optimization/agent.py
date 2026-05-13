from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, FinalOutput
from acs_shared.constants import AgentName, AgentStatus


class OptimizationAgent(BaseAgent):
    """Optimization Agent: polishes final tone, style, and length."""

    def __init__(self):
        super().__init__(name=AgentName.OPTIMIZATION)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # Phase 1: return dummy polished content
        draft = input.context.draft
        if draft is not None:
            polished = f'{draft.content}\n\n[Optimized: tone improved, style refined, factual content preserved.]'
        else:
            polished = (
                f'Polished content about {input.topic}. '
                f'[Optimized: tone improved, style refined, factual content preserved.]'
            )
        output = FinalOutput(
            content=polished,
            word_count=len(polished.split()),
            tone='professional',
        )
        input.context.set('final', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.OPTIMIZATION,
            result=output.model_dump_json(),
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=30,
                latency_ms=100,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = OptimizationAgent()
