"""Writing Agent — stub for Member 3.

TODO: Generate full prose content from the outline, following the
outline structure exactly. Minimum 500 words, maximum 2000 words.
"""

import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, DraftOutput
from acs_shared.constants import AgentName, AgentStatus

logger = logging.getLogger(__name__)


class WritingAgent(BaseAgent):
    """Writing Agent — generates full content from the outline.

    **Instructions for Member 3 — implement execute():**

    1. Read the outline from context:
       ``outline = input.context.outline``
    2. Build a text representation of the outline with all sections
       and key points
    3. (Phase 2) Query LightRAG for additional context:
       ``rag_context = await self.retrieve_from_memory(input.topic, mode='hybrid')``
    4. Load the writing prompt from ``prompts/writing.md``
    5. Append the topic, full outline, and any RAG context
    6. Call the LLM: ``text, tokens, latency = await self.generate_text(prompt)``
    7. Create a ``DraftOutput(content=..., word_count=len(text.split()))``
    8. Save it: ``input.context.set('draft', output)``
    9. Return ``AgentOutput`` with ``AgentStatus.SUCCESS``

    **Contract:**
    - ``input.context.draft`` → ``DraftOutput`` after execute
    - Follow the outline structure exactly — do NOT invent new sections
    - Output must be clean prose, no markdown headers or bullet points
    - Minimum 500 words, maximum 2000 words
    - Always use ``self.generate_text()`` — never call an LLM SDK directly
    """

    def __init__(self):
        super().__init__(name=AgentName.WRITING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # --- YOUR CODE HERE ---
        outline_text = ''
        if input.context.outline:
            for section in input.context.outline.sections:
                outline_text += f"### {section.heading}\n"
                for point in section.key_points:
                    outline_text += f"- {point}\n"

        prompt = self.load_prompt('writing')
        prompt += (
            f"\n\nTopic: {input.topic}\n"
            f"Outline:\n{outline_text}\n"
        )

        text, tokens, latency = await self.generate_text(prompt)

        output = DraftOutput(
            content=text.strip(),
            word_count=len(text.split()),
        )
        input.context.set('draft', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.WRITING,
            result=output.content,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = WritingAgent()
