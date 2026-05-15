"""Optimization Agent — stub for Member 5.

TODO: Polish the final content — refine tone, style, and length
without changing substance. Preserve all factual content from the
draft — no hallucinations.
"""

import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, FinalOutput
from acs_shared.constants import AgentName, AgentStatus

logger = logging.getLogger(__name__)


class OptimizationAgent(BaseAgent):
    """Optimization Agent — polishes the final output.

    **Instructions for Member 5 — implement execute():**

    1. Read the draft and edit notes from context:
       ``draft_text = input.context.draft.content if input.context.draft else ''``
       ``edit_notes = input.context.edit.instructions if input.context.edit else ''``
    2. Load the optimization prompt from ``prompts/optimization.md``
    3. Append the topic, draft text, and edit notes
    4. Call the LLM: ``text, tokens, latency = await self.generate_text(prompt)``
    5. Create a ``FinalOutput(content=..., word_count=..., tone=...)``
       — determine the tone from the content (professional, conversational, etc.)
    6. Save it: ``input.context.set('final', output)``
    7. Return ``AgentOutput`` with ``AgentStatus.SUCCESS``

    **Rules:**
    - Preserve ALL factual content — do not add, remove, or change facts
    - Refine tone, style, and length only
    - Output must be clean, publishable content — no metadata or scores
    - Always use ``self.generate_text()`` — never call an LLM SDK directly

    **Contract:**
    - ``input.context.final`` → ``FinalOutput`` after execute
    - ``final.content`` is the final deliverable to the user
    """

    def __init__(self):
        super().__init__(name=AgentName.OPTIMIZATION)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # --- YOUR CODE HERE ---
        draft_text = (
            input.context.draft.content
            if input.context.draft else ''
        )
        edit_notes = (
            input.context.edit.instructions
            if input.context.edit else ''
        )

        prompt = self.load_prompt('optimization')
        prompt += (
            f"\n\nTopic: {input.topic}\n"
            f"Draft:\n{draft_text}\n"
            f"Edit Notes:\n{edit_notes}\n"
        )

        text, tokens, latency = await self.generate_text(prompt)

        output = FinalOutput(
            content=text.strip(),
            word_count=len(text.split()),
            tone='professional',
        )
        input.context.set('final', output)

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.OPTIMIZATION,
            result=output.content,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = OptimizationAgent()
