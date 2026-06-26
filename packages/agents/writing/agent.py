"""Writing Agent — Member 3 implementation.

Generates clean, structured prose from the Planning Agent's outline.
On retry iterations, incorporates Editing Agent feedback automatically.

Pipeline position: 3rd agent in the SequentialAgent.
  Research → Planning → [Writing → Editing (loop x3)] → Optimization
"""

import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, DraftOutput
from acs_shared.constants import AgentName, AgentStatus

logger = logging.getLogger(__name__)

# Architecture spec constraints
_MIN_WORDS = 500
_MAX_WORDS = 2000


class WritingAgent(BaseAgent):
    """Writing Agent — generates full prose content from a structured outline.

    Responsibilities
    ----------------
    1. Read ``context.outline`` (OutlineOutput) from Planning Agent.
    2. Check ``context.edit.instructions`` if this is a retry iteration and
       weave the feedback into the revised draft.
    3. Query LightRAG for additional research context (Phase 2 — no-op now).
    4. Build a rich generation prompt and call the LLM.
    5. Store the result as ``DraftOutput`` in ``context.draft``.
    6. Return ``AgentOutput(status=SUCCESS)``.

    Retry behaviour
    ---------------
    The Editing Agent returns ``status=RETRY`` when the average quality score
    is below 7.0 / 10. The Orchestrator's LoopAgent (max 3 iterations) then:
      - Calls ``context.overwrite('draft', None)``  — clears the previous draft
      - Re-runs  WritingAgent → EditingAgent

    This agent detects a retry by checking whether ``context.edit`` is already
    set (meaning the Editing Agent ran at least once) and reads the
    ``instructions`` field to improve the next draft.
    """

    def __init__(self):
        super().__init__(name=AgentName.WRITING)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_outline(self, outline) -> str:
        """Convert OutlineOutput into a readable numbered block for the prompt."""
        if not outline:
            return ''
        lines = [f'Title: {outline.title}', '']
        for idx, section in enumerate(outline.sections, 1):
            lines.append(f'Section {idx} — {section.heading}')
            for point in section.key_points:
                lines.append(f'  • {point}')
            lines.append('')
        return '\n'.join(lines).strip()

    def _build_prompt(
        self,
        base_prompt: str,
        topic: str,
        outline_text: str,
        rag_context: str,
        edit_instructions: str | None,
        retry_count: int,
    ) -> str:
        """Assemble the full generation prompt from its constituent parts."""
        parts = [base_prompt]

        # ── Topic ──────────────────────────────────────────────────────
        parts.append(f'\n\n---\n## TOPIC\n{topic}')

        # ── Outline ────────────────────────────────────────────────────
        if outline_text:
            parts.append(
                f'\n## CONTENT OUTLINE\n'
                f'Follow these sections IN ORDER. Expand each into 2-3 paragraphs.\n\n'
                f'{outline_text}'
            )
        else:
            # Fallback when planning agent produced nothing (e.g. in unit tests)
            parts.append(
                f'\n## TASK\n'
                f'Write a comprehensive, well-structured article about: {topic}'
            )

        # ── RAG context (Phase 2 enrichment) ───────────────────────────
        if rag_context and rag_context.strip():
            parts.append(
                f'\n## RESEARCH CONTEXT\n'
                f'Use the following factual information where relevant:\n\n{rag_context}'
            )

        # ── Retry / revision instructions ──────────────────────────────
        if edit_instructions and retry_count > 0:
            parts.append(
                f'\n## ⚠️  REVISION REQUIRED (Attempt #{retry_count + 1})\n'
                f'Your previous draft was reviewed and needs these specific improvements:\n\n'
                f'{edit_instructions}\n\n'
                f'Address EVERY point above in this revised version.'
            )

        # ── Hard output constraints ─────────────────────────────────────
        parts.append(
            f'\n## OUTPUT REQUIREMENTS\n'
            f'- Length: {_MIN_WORDS}–{_MAX_WORDS} words of body text\n'
            f'- Format: plain prose paragraphs ONLY\n'
            f'- NO markdown headers (##, ###), NO bold (**text**), NO italics\n'
            f'- NO bullet points or numbered lists\n'
            f'- Start the article directly — no preamble, no meta-commentary\n'
            f'- Do NOT invent facts beyond what is in the outline and research context\n'
            f'- Smooth, logical transitions between sections\n'
        )

        return '\n'.join(parts)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def execute(self, input: AgentInput) -> AgentOutput:
        """Generate prose draft from outline, incorporating retry feedback.

        Parameters
        ----------
        input : AgentInput
            Standard pipeline input. Relevant context fields:
            - ``input.context.outline``  — OutlineOutput from Planning Agent
            - ``input.context.edit``     — EditOutput from previous Editing
                                           iteration (None on first run)

        Returns
        -------
        AgentOutput
            - ``result``  : full draft text
            - ``status``  : SUCCESS
            - context key : ``draft`` (DraftOutput)
        """
        # ── Step 1: Read outline ───────────────────────────────────────
        outline = input.context.outline
        outline_text = self._format_outline(outline)

        # ── Step 2: Read retry context ─────────────────────────────────
        edit_ctx = input.context.edit
        edit_instructions: str | None = None
        retry_count = 0

        if edit_ctx is not None:
            edit_instructions = edit_ctx.instructions
            retry_count = edit_ctx.retry_count
            logger.info(
                f'WritingAgent retry #{retry_count} for job {input.job_id}. '
                f'Instructions: {str(edit_instructions)[:120]}'
            )

        # ── Step 3: Query LightRAG (Phase 2 – currently no-op) ─────────
        rag_context = ''
        try:
            rag_context = await self.retrieve_from_memory(
                input.topic, mode='hybrid'
            )
        except Exception as rag_err:
            logger.debug(f'LightRAG retrieval skipped: {rag_err}')

        # ── Step 4: Build prompt ───────────────────────────────────────
        base_prompt = self.load_prompt('writing')
        prompt = self._build_prompt(
            base_prompt=base_prompt,
            topic=input.topic,
            outline_text=outline_text,
            rag_context=rag_context,
            edit_instructions=edit_instructions,
            retry_count=retry_count,
        )

        # ── Step 5: Call LLM ───────────────────────────────────────────
        try:
            text, tokens, latency = await self.generate_text(prompt)
        except Exception as exc:
            logger.error(f'LLM call failed in WritingAgent: {exc}')
            return AgentOutput(
                job_id=input.job_id,
                agent=AgentName.WRITING,
                result='',
                metadata=AgentMetadata(
                    config=input.config,
                    tokens_used=0,
                    latency_ms=0,
                    retry_count=retry_count,
                    error=str(exc),
                ),
                status=AgentStatus.FAILED,
            )

        # ── Step 6: Validate content ───────────────────────────────────
        content = text.strip()
        word_count = len(content.split()) if content else 0

        logger.info(
            f'WritingAgent produced {word_count} words '
            f'(retry={retry_count}, job={input.job_id})'
        )

        if word_count == 0:
            logger.warning(f'WritingAgent: empty content for job {input.job_id}')

        # ── Step 7: Save to pipeline context ──────────────────────────
        draft = DraftOutput(
            content=content,
            word_count=word_count,
        )
        input.context.set('draft', draft)

        # ── Step 8: Return ─────────────────────────────────────────────
        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.WRITING,
            result=draft.content,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
                retry_count=retry_count,
            ),
            status=AgentStatus.SUCCESS,
        )


# ADK Web entrypoint — discovered by `uv run adk web`
root_agent = WritingAgent()
