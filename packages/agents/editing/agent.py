from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, EditOutput, EditScores
from acs_shared.constants import AgentName, AgentStatus


class EditingAgent(BaseAgent):
    """Editing Agent: scores draft quality, decides pass/retry."""

    def __init__(self):
        super().__init__(name=AgentName.EDITING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        retry_count = input.context.edit.retry_count if input.context.edit else 0

        # Phase 1: fail progressively (dummy) so retry loop can be tested
        scores = EditScores(coherence=8, relevance=8, completeness=8)
        avg = (scores.coherence + scores.relevance + scores.completeness) / 3
        # First call passes; retries always pass (dummy mode)
        passed = avg >= 7.0

        output = EditOutput(
            scores=scores,
            average=avg,
            passed=passed,
            retry_count=retry_count,
            instructions=None if passed else 'Improve clarity and add more details in section 2.',
        )
        input.context.set('edit', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.EDITING,
            result=output.model_dump_json(),
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=40,
                latency_ms=150,
                retry_count=retry_count,
            ),
            status=AgentStatus.SUCCESS if passed else AgentStatus.RETRY,
        )


root_agent = EditingAgent()
