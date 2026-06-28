"""
Optimization Agent — Member 5.

"""
import logging

from acs_shared.base_agent import BaseAgent
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.schemas import (
    AgentInput,
    AgentMetadata,
    AgentOutput,
    ContextWriteError,
    FinalOutput,
)

logger = logging.getLogger(__name__)

# Keyword heuristics used to guess a tone label for the polished content.
# This is a lightweight, dependency-free classifier — it does not call the
# LLM a second time and does not affect billing/latency. It only inspects
# the text the Optimization LLM call already produced.
_CONVERSATIONAL_MARKERS = (
    "you know", "hey", "well,", "let's", "lets ", "honestly", "basically",
    "kind of", "sort of", "gonna", "wanna", "we've all", "imagine",
)
_ACADEMIC_MARKERS = (
    "study shows", "research indicates", "studies have shown",
    "according to research", "data suggests", "evidence suggests",
    "literature review", "empirical", "hypothesis", "methodology",
)

# Sensible bounds so a degenerate LLM response (empty string, or a wall of
# repeated tokens) can't silently become "the final answer" for the user.
_MIN_VALID_WORD_COUNT = 3


class OptimizationAgent(BaseAgent):
    """Polishes the final draft into publishable content.

    Contract:
        - Reads `input.context.draft` (DraftOutput) and `input.context.edit`
          (EditOutput) written by upstream agents.
        - Writes `input.context.final` (FinalOutput) exactly once.
        - Returns AgentOutput with `result` set to the polished text.
    """

    def __init__(self):
        super().__init__(name=AgentName.OPTIMIZATION)

    async def execute(self, input: AgentInput) -> AgentOutput:
        try:
            return await self._execute(input)
        except Exception as exc:  # noqa: BLE001 - agents must never crash
            logger.exception(
                "Optimization agent failed for job_id=%s", input.job_id
            )
            return self._failure_output(input, exc)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    async def _execute(self, input: AgentInput) -> AgentOutput:
        draft_text = self._read_draft(input)
        edit_notes = self._read_edit_notes(input)

        if not draft_text.strip():
            # Nothing to polish — fail loudly rather than inventing content.
            # Inventing content here would violate "preserve all factual
            # content / never add facts", since there would be no source
            # of facts to preserve.
            return self._failure_output(
                input,
                ValueError("No draft content available to optimize."),
            )

        prompt = self._build_prompt(
            topic=input.topic,
            draft_text=draft_text,
            edit_notes=edit_notes,
        )

        text, tokens, latency = await self.generate_text(prompt)

        polished = text.strip()
        if len(polished.split()) < _MIN_VALID_WORD_COUNT:
            # Defensive guard: an empty/near-empty LLM response should not
            # silently overwrite a perfectly good draft as the "final" text.
            return self._failure_output(
                input,
                ValueError(
                    f"Optimization output too short ({len(polished.split())} "
                    "words) — refusing to publish."
                ),
                tokens=tokens,
                latency=latency,
            )

        tone = self._infer_tone(polished)

        output = FinalOutput(
            content=polished,
            word_count=len(polished.split()),
            tone=tone,
        )

        try:
            input.context.set("final", output)
        except ContextWriteError as exc:
            # Context is append-only by design (see PipelineContext.set).
            # If `final` is already populated this run is a duplicate
            # execution — don't crash the pipeline, report it instead.
            logger.warning(
                "Context key 'final' already set for job_id=%s: %s",
                input.job_id, exc,
            )
            return self._failure_output(input, exc, tokens=tokens, latency=latency)

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_draft(input: AgentInput) -> str:
        draft = input.context.draft
        return draft.content if draft else ""

    @staticmethod
    def _read_edit_notes(input: AgentInput) -> str:
        edit = input.context.edit
        return edit.instructions if (edit and edit.instructions) else ""

    def _build_prompt(self, topic: str, draft_text: str, edit_notes: str) -> str:
        prompt = self.load_prompt("optimization")
        prompt += (
            f"\n\nTopic: {topic}\n"
            f"Draft:\n{draft_text}\n"
            f"Edit Notes:\n{edit_notes or 'None'}\n\n"
            "Polish this content:\n"
            "- Refine the tone (make it professional, clear, and engaging)\n"
            "- Improve sentence flow and readability\n"
            "- Preserve ALL factual content — do NOT change facts, numbers, "
            "names, or claims\n"
            "- Do NOT add new facts or remove existing ones\n"
            "- Keep the same structure and approximate length\n"
            "- Output clean, publishable text only — no headers like "
            "'Final Output:', no meta-commentary, no scores\n"
        )
        return prompt

    @staticmethod
    def _infer_tone(text: str) -> str:
        """Cheap keyword-based tone classifier.

        Default is 'professional'. Falls back to 'conversational' or
        'academic' if their respective markers dominate. This never calls
        the LLM again — it only inspects text already generated.
        """
        lowered = text.lower()

        conversational_hits = sum(1 for w in _CONVERSATIONAL_MARKERS if w in lowered)
        academic_hits = sum(1 for w in _ACADEMIC_MARKERS if w in lowered)

        if conversational_hits == 0 and academic_hits == 0:
            return "professional"
        if academic_hits >= conversational_hits:
            return "academic"
        return "conversational"

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
            agent=AgentName.OPTIMIZATION,
            result="",
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
                error=str(exc),
            ),
            status=AgentStatus.FAILED,
        )


root_agent = OptimizationAgent()
