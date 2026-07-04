"""Research Agent — Member 1 implementation.

Searches the web for the user's topic, extracts content from the top
results, saves findings to LightRAG, and summarizes everything for
downstream agents (Planning).

Pipeline position: 1st agent in the SequentialAgent.
  [Research] → Planning → [Writing → Editing (loop x3)] → Optimization
"""

import logging

from acs_shared.base_agent import BaseAgent
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.schemas import AgentInput, AgentMetadata, AgentOutput, ResearchOutput
from acs_shared.utils import extract_facts, parse_sources

from .tools.scrape import scrape_content
from .tools.search import web_search

logger = logging.getLogger(__name__)

# How many search results to scrape content from.
_TOP_N_RESULTS = 5
_MIN_VALID_WORD_COUNT = 3


class ResearchAgent(BaseAgent):
    """Research Agent — web search, content extraction, and summarization.

    Contract:
        - Runs a web search for `input.topic`.
        - Extracts content from the top N results.
        - Saves extracted findings to LightRAG (no-op in Phase 1).
        - Writes `input.context.research` (ResearchOutput) exactly once.
        - Returns AgentOutput with `result` set to the research summary.
    """

    def __init__(self):
        super().__init__(name=AgentName.RESEARCH)

    async def execute(self, input: AgentInput) -> AgentOutput:
        try:
            return await self._execute(input)
        except Exception as exc:  # noqa: BLE001 - agents must never crash
            logger.exception('Research agent failed for job_id=%s', input.job_id)
            return self._failure_output(input, exc)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    async def _execute(self, input: AgentInput) -> AgentOutput:
        # ── Step 1: Web search (Open-WebSearch MCP) ──────────────────────
        try:
            results = await web_search(input.topic, num_results=_TOP_N_RESULTS)
        except Exception as exc:
            logger.warning(f"Web search failed for '{input.topic}': {exc}")
            results = []

        # ── Step 2: Scrape content from top results (Scrapling) ──────────
        scraped = await self._scrape_results(results)

        # ── Step 3: Save findings to LightRAG (Phase 1: no-op) ────────────
        for item in scraped:
            try:
                await self.save_to_memory(
                    text=item['content'],
                    metadata={'topic': input.topic, 'source': item['url']},
                )
            except Exception as exc:
                logger.debug(f'save_to_memory skipped for {item["url"]}: {exc}')

        # ── Step 4: Build prompt ───────────────────────────────────────────
        prompt = self._build_prompt(input.topic, scraped)

        # ── Step 5: Call LLM ───────────────────────────────────────────────
        try:
            text, tokens, latency = await self.generate_text(prompt)
        except Exception as exc:
            logger.error(f'LLM call failed in ResearchAgent: {exc}')
            return self._failure_output(input, exc)

        summary = text.strip()
        if len(summary.split()) < _MIN_VALID_WORD_COUNT:
            return self._failure_output(
                input,
                ValueError(
                    f'Research summary too short ({len(summary.split())} '
                    'words) — refusing to publish.'
                ),
                tokens=tokens,
                latency=latency,
            )

        # ── Step 6: Derive facts & sources deterministically ──────────────
        raw_content = '\n\n'.join(item['content'] for item in scraped) or summary
        facts = extract_facts(raw_content)
        if not facts:
            facts = extract_facts(summary)

        sources = [item['url'] for item in scraped if item.get('url')]
        if not sources:
            sources = parse_sources(text)

        output = ResearchOutput(
            summary=summary,
            facts=facts,
            sources=sources,
            raw=raw_content,
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _scrape_results(self, results: list[dict]) -> list[dict]:
        """Scrape content for each search result. Never raises — a failed
        scrape for one URL shouldn't take down the whole research step."""
        scraped = []
        for item in results[:_TOP_N_RESULTS]:
            url = item.get('url', '')
            if not url:
                continue
            try:
                content = await scrape_content(url)
            except Exception as exc:
                logger.debug(f'scrape_content failed for {url}: {exc}')
                content = item.get('description', '')
            scraped.append(
                {
                    'title': item.get('title', ''),
                    'url': url,
                    'content': content,
                }
            )
        return scraped

    def _build_prompt(self, topic: str, scraped: list[dict]) -> str:
        prompt = self.load_prompt('research')
        prompt += f'\n\nTopic: {topic}\n'

        if scraped:
            prompt += '\nSearch Results:\n'
            for i, item in enumerate(scraped, 1):
                prompt += f'\n{i}. {item["title"]} ({item["url"]})\n{item["content"][:800]}\n'
        else:
            prompt += '\n(No search results available — rely on general knowledge.)\n'

        return prompt

    def _failure_output(
        self,
        input: AgentInput,
        exc: Exception,
        tokens: int = 0,
        latency: int = 0,
    ) -> AgentOutput:
        """Build a well-formed AgentOutput for the failure path.

        Per the agent contract, agents must always return AgentOutput with
        all fields filled — never raise out of execute().
        """
        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.RESEARCH,
            result='',
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
                error=str(exc),
            ),
            status=AgentStatus.FAILED,
        )


root_agent = ResearchAgent()
