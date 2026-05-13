from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata
from acs_shared.constants import AgentName, AgentStatus


class OrchestratorAgent(BaseAgent):
    """Orchestrator Agent: manages the pipeline, no content generation."""

    def __init__(self):
        super().__init__(name=AgentName.ORCHESTRATOR)

    async def execute(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.ORCHESTRATOR,
            result='Pipeline orchestration complete',
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=10,
                latency_ms=50,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = OrchestratorAgent()
