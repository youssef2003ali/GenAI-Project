from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, OutlineOutput, OutlineSection
from acs_shared.constants import AgentName, AgentStatus


class PlanningAgent(BaseAgent):
    """Planning Agent: generates structured outline from research."""

    def __init__(self):
        super().__init__(name=AgentName.PLANNING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # Phase 1: return hardcoded dummy outline
        output = OutlineOutput(
            title=f'Structured Content: {input.topic}',
            sections=[
                OutlineSection(
                    heading='Introduction',
                    key_points=['Overview of the topic', 'Context and background information'],
                ),
                OutlineSection(
                    heading='Main Concepts',
                    key_points=['Core concepts and definitions', 'Detailed analysis', 'Practical examples'],
                ),
                OutlineSection(
                    heading='Conclusion',
                    key_points=['Summary of findings', 'Key takeaways and implications'],
                ),
            ],
        )
        input.context.set('outline', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.PLANNING,
            result=output.model_dump_json(),
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=30,
                latency_ms=80,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = PlanningAgent()
