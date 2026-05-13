from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, DraftOutput
from acs_shared.constants import AgentName, AgentStatus


class WritingAgent(BaseAgent):
    """Writing Agent: generates full content from outline."""

    def __init__(self):
        super().__init__(name=AgentName.WRITING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # Phase 1: return dummy draft content
        content = (
            f'This is a generated draft about {input.topic}. '
            f'It follows the outline structure provided by the planning agent. '
        ) * 30
        output = DraftOutput(
            content=content,
            word_count=len(content.split()),
        )
        input.context.set('draft', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.WRITING,
            result=output.model_dump_json(),
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=100,
                latency_ms=200,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = WritingAgent()
