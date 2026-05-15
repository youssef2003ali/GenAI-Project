"""Planning Agent — stub for Member 2.

TODO: Query LightRAG for context, then generate a structured outline
with 3-7 sections from the research.
"""

import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import (
    AgentInput, AgentOutput, AgentMetadata,
    OutlineOutput, OutlineSection,
)
from acs_shared.constants import AgentName, AgentStatus

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    """Planning Agent — generates a structured outline from research.

    **Instructions for Member 2 — implement execute():**

    1. Read the research summary from context:
       ``research_summary = input.context.research.summary if input.context.research else ''``
    2. (Phase 2) Query LightRAG for additional context:
       ``rag_context = await self.retrieve_from_memory(input.topic, mode='hybrid')``
    3. Load the planning prompt from ``prompts/planning.md``
    4. Append the topic, research summary, and any RAG context
    5. Call the LLM: ``text, tokens, latency = await self.generate_text(prompt)``
    6. Parse the LLM output into an ``OutlineOutput`` with 3-7 ``OutlineSection``
       entries, each with a ``heading`` and ``key_points`` list
    7. Save it: ``input.context.set('outline', output)``
    8. Return ``AgentOutput`` with ``AgentStatus.SUCCESS``

    **Contract:**
    - ``input.context.outline`` → ``OutlineOutput`` after execute
    - Sections must have **min 3, max 7** sections
    - Never hardcode model names — read from ``input.config``
    - Always use ``self.generate_text()`` — never call an LLM SDK directly
    """

    def __init__(self):
        super().__init__(name=AgentName.PLANNING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # --- YOUR CODE HERE ---
        research_summary = (
            input.context.research.summary
            if input.context.research else ''
        )

        prompt = self.load_prompt('planning')
        prompt += (
            f"\n\nTopic: {input.topic}\n"
            f"Research Summary:\n{research_summary}\n"
        )

        text, tokens, latency = await self.generate_text(prompt)

        # Parse sections from LLM output (## headings, - bullet points)
        sections = []
        current_heading = None
        current_points = []
        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                continue
            if clean.startswith('###') or clean.startswith('##'):
                if current_heading:
                    sections.append(
                        OutlineSection(
                            heading=current_heading,
                            key_points=current_points[:5],
                        )
                    )
                current_heading = clean.lstrip('#').strip()
                current_points = []
            elif clean.startswith('-') and current_heading:
                current_points.append(clean.lstrip('-').strip())

        if current_heading:
            sections.append(
                OutlineSection(
                    heading=current_heading,
                    key_points=current_points[:5],
                )
            )

        if not sections:
            sections = [
                OutlineSection(
                    heading='Outline',
                    key_points=[text[:300].strip()],
                )
            ]

        output = OutlineOutput(
            title=f'Outline for {input.topic}',
            sections=sections,
        )
        input.context.set('outline', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.PLANNING,
            result=text,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = PlanningAgent()
