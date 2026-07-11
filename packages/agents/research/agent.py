"""Research Agent — searches the web, extracts content, saves to LightRAG."""

import logging

from acs_shared.base_agent import BaseAgent
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.schemas import AgentInput, AgentMetadata, AgentOutput, ResearchOutput
from acs_shared.utils import extract_facts, parse_sources

from .tools.scrape import scrape_content
from .tools.search import web_search

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Research Agent — searches the web, extracts content, saves to LightRAG."""

    def __init__(self):
        super().__init__(name=AgentName.RESEARCH)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # 1. Web search
        results = await web_search(input.topic, num_results=5)

        # 2. Scrape top results
        scraped_chunks = []
        for r in results[:5]:
            try:
                content = await scrape_content(r['url'])
                scraped_chunks.append(f'Source: {r["url"]}\n{content}')
            except Exception as exc:
                logger.warning(f'Scrape failed for {r["url"]}: {exc}')

        combined_content = '\n\n'.join(scraped_chunks)

        # 3. Save to LightRAG (currently a no-op stub, safe to call)
        if combined_content:
            await self.save_to_memory(
                text=combined_content,
                metadata={'topic': input.topic},
            )

        # 4. Build prompt with real search context
        prompt = self.load_prompt('research')
        prompt += f'\n\nTopic: {input.topic}'
        if combined_content:
            prompt += f'\n\nSearch Results:\n{combined_content}'

        # 5. Call LLM
        text, tokens, latency = await self.generate_text(prompt)

        # 6. Parse facts/sources — from LLM text AND raw scraped content
        facts = extract_facts(text) or extract_facts(combined_content)
        sources = parse_sources(text) or [r['url'] for r in results]

        # 7. Save to context & return
        output = ResearchOutput(
            summary=text[:1200],
            facts=facts,
            sources=sources,
            raw=combined_content or text,
        )
        input.context.set('research', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.RESEARCH,
            result=output.summary,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = ResearchAgent()
