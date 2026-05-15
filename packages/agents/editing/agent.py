"""Editing Agent — stub for Member 4.

TODO: Score the draft on coherence, relevance, and completeness
(0-10 each). If average < 7.0, return RETRY with improvement
instructions. Maximum 3 retries.
"""

import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import (
    AgentInput, AgentOutput, AgentMetadata,
    EditOutput, EditScores,
)
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.utils import parse_edit_scores

logger = logging.getLogger(__name__)


class EditingAgent(BaseAgent):
    """Editing Agent — scores draft quality and decides pass/retry.

    **Instructions for Member 4 — implement execute():**

    1. Read the draft from context:
       ``draft_text = input.context.draft.content if input.context.draft else ''``
    2. Load the editing prompt from ``prompts/editing.md``
    3. Append the topic and the full draft text
    4. Call the LLM: ``text, tokens, latency = await self.generate_text(prompt)``
    5. Parse the LLM output for scores: coherence, relevance, completeness
       (each 0-10). Use ``parse_edit_scores(text)`` from utils as a starting point.
    6. Calculate average. If average >= 7.0: set status to SUCCESS.
       If average < 7.0: set status to RETRY, include improvement instructions.
    7. Create ``EditOutput(scores=EditScores(...), average=..., passed=..., instructions=...)``
    8. Save it: ``input.context.set('edit', output)``
    9. Return ``AgentOutput`` with appropriate status (SUCCESS or RETRY)

    **Retry logic:**
    - The Orchestrator's LoopAgent handles the retry cycle automatically.
    - Simply return RETRY status — the pipeline will re-run Writing → Editing.
    - Maximum 3 retries enforced by LoopAgent's ``max_iterations=3``.
    - After 3rd retry, pass forward regardless of score.

    **Contract:**
    - ``input.context.edit`` → ``EditOutput`` after execute
    - RETRY status triggers a Writing → Editing loop in the pipeline
    - Always use ``self.generate_text()`` — never call an LLM SDK directly
    """

    def __init__(self):
        super().__init__(name=AgentName.EDITING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # --- YOUR CODE HERE ---
        draft_text = (
            input.context.draft.content
            if input.context.draft else ''
        )

        prompt = self.load_prompt('editing')
        prompt += f"\n\nTopic: {input.topic}\nDraft:\n{draft_text}\n"

        text, tokens, latency = await self.generate_text(prompt)

        # Parse scores from LLM output
        scores = parse_edit_scores(text)
        avg = scores['average']
        passed = scores['passed']

        output = EditOutput(
            scores=EditScores(
                coherence=scores['coherence'],
                relevance=scores['relevance'],
                completeness=scores['completeness'],
            ),
            average=avg,
            passed=passed,
            retry_count=(
                input.context.edit.retry_count if input.context.edit else 0
            ),
            instructions=scores['issues'],
        )
        input.context.set('edit', output)

        status = AgentStatus.SUCCESS if passed else AgentStatus.RETRY

        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.EDITING,
            result=text,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
                retry_count=output.retry_count,
            ),
            status=status,
        )


root_agent = EditingAgent()
