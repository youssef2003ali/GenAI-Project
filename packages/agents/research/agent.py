from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, ResearchOutput
from acs_shared.constants import AgentName, AgentStatus


class ResearchAgent(BaseAgent):
    """Research Agent: searches web, extracts content, saves to LightRAG."""

    def __init__(self):
        super().__init__(name=AgentName.RESEARCH)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # Phase 1: return hardcoded dummy research output
        topic = input.topic
        output = ResearchOutput(
            summary=(
                f'Research findings about: {topic}. '
                f'Comprehensive analysis reveals key insights and data points '
                f'across multiple authoritative sources. The topic {topic} has '
                f'been extensively studied with significant findings in recent years. '
                f'Multiple peer-reviewed studies confirm the importance of understanding '
                f'{topic} for advancing scientific knowledge and practical applications. '
                f'Experts estimate that research in this area has grown by approximately '
                f'40 percent over the last decade.'
            ),
            facts=[
                f'Research shows that {topic} is a rapidly evolving field with significant implications for science and industry.',
                f'Studies indicate that investment in {topic} research grew by 40 percent over the last decade.',
                f'Multiple peer-reviewed papers published in 2023 confirm the importance of {topic} for advancing human knowledge.',
                f'Experts estimate that practical applications of {topic} could emerge within 5 to 10 years.',
                f'International collaboration on {topic} has increased, with researchers from 30+ countries contributing.',
            ],
            sources=[
                'Nature Research Journal (2023) - Comprehensive review of recent advances in the field',
                'Science Direct (2024) - Meta-analysis of industry trends and research priorities',
                'IEEE Transactions (2023) - Technical overview of methodologies and applications',
                'MIT Technology Review (2024) - Expert interviews and market analysis',
                'Stanford University Research Database (2023) - Longitudinal study of research output',
            ],
            raw=f'Raw extracted content from web search results for topic: {topic}',
        )
        input.context.set('research', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.RESEARCH,
            result=output.model_dump_json(),
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=50,
                latency_ms=100,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = ResearchAgent()
