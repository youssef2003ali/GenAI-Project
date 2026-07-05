"""
Manual smoke-test for the Editing Agent.

Runs the agent with a FAKE (mocked) LLM response so you can check
the parsing / pass-or-retry logic WITHOUT needing a real API key.

Run with:
    uv run python manual_test.py
"""

import asyncio
from unittest.mock import AsyncMock

from agent import root_agent
from acs_shared.schemas import AgentInput, PipelineContext, AgentConfig, DraftOutput


async def run_case(label: str, fake_llm_response: str, draft_text: str = "This is a sample draft about AI."):
    print(f"\n{'='*60}\n{label}\n{'='*60}")

    # Build a fake pipeline context with a draft already in it
    context = PipelineContext()
    context.draft = DraftOutput(content=draft_text, word_count=len(draft_text.split()))

    agent_input = AgentInput(
        job_id="manual-test-1",
        topic="Artificial Intelligence",
        context=context,
        config=AgentConfig(),
    )

    # Mock generate_text so we don't call a real LLM / need an API key
    root_agent.generate_text = AsyncMock(
        return_value=(fake_llm_response, 123, 456)
    )

    output = await root_agent.execute(agent_input)

    print("status        :", output.status)
    print("edit.scores   :", context.edit.scores if context.edit else None)
    print("edit.average  :", context.edit.average if context.edit else None)
    print("edit.passed   :", context.edit.passed if context.edit else None)
    print("edit.instructions:", context.edit.instructions if context.edit else None)


async def main():
    # Case 1: high scores -> should PASS (status = SUCCESS)
    await run_case(
        "Case 1: Good draft (expect SUCCESS)",
        fake_llm_response="""
Coherence: 9
Relevance: 8
Completeness: 9
Average: 8.7
Decision: PASS
Issues:
- None
""",
    )

    # Case 2: low scores -> should RETRY
    await run_case(
        "Case 2: Weak draft (expect RETRY)",
        fake_llm_response="""
Coherence: 5
Relevance: 6
Completeness: 4
Average: 5.0
Decision: RETRY
Issues:
- Add more detail to the second section
- Fix the transition between paragraphs 2 and 3
""",
    )

    # Case 3: empty draft -> should FAIL (tests your try/except + ValueError)
    await run_case(
        "Case 3: Empty draft (expect FAILED)",
        fake_llm_response="irrelevant, won't be reached",
        draft_text="",
    )


if __name__ == "__main__":
    asyncio.run(main())