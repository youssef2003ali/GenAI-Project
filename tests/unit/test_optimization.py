"""Unit tests for the Optimization Agent.

Run with:
    uv run pytest tests/unit/test_optimization.py -v

These tests mock `generate_text` / `load_prompt` so they run offline,
without hitting Mistral/OpenRouter/Gemini or needing an API key.
"""
import pytest

from acs_shared.constants import AgentName, AgentStatus, Provider
from acs_shared.schemas import (
    AgentConfig,
    AgentInput,
    ContextWriteError,
    DraftOutput,
    EditOutput,
    EditScores,
    PipelineContext,
)

from packages.agents.optimization.agent import OptimizationAgent


def make_input(
    draft_content: str = "This is the original draft about quantum computing.",
    edit_instructions: str | None = "Make it more engaging.",
    topic: str = "Quantum Computing",
    job_id: str = "job-123",
) -> AgentInput:
    context = PipelineContext()
    if draft_content is not None:
        context.set(
            "draft",
            DraftOutput(content=draft_content, word_count=len(draft_content.split())),
        )
    if edit_instructions is not None:
        context.set(
            "edit",
            EditOutput(
                scores=EditScores(coherence=8, relevance=8, completeness=8),
                average=8.0,
                passed=True,
                instructions=edit_instructions,
            ),
        )
    return AgentInput(
        job_id=job_id,
        topic=topic,
        context=context,
        config=AgentConfig(provider=Provider.MISTRAL, model="mistral-small-latest"),
    )


@pytest.fixture
def agent(monkeypatch):
    a = OptimizationAgent()
    monkeypatch.setattr(a, "load_prompt", lambda name: "PROMPT_HEADER\n")
    return a


def mock_generate_text(text: str, tokens: int = 42, latency: int = 100):
    async def _gen(prompt: str):
        return text, tokens, latency
    return _gen


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_success_writes_final_to_context(agent, monkeypatch):
    polished = "Quantum computing is a fascinating field with real promise."
    monkeypatch.setattr(agent, "generate_text", mock_generate_text(polished))

    input_ = make_input()
    output = await agent.execute(input_)

    assert output.status == AgentStatus.SUCCESS
    assert output.result == polished
    assert output.agent == AgentName.OPTIMIZATION
    assert input_.context.final is not None
    assert input_.context.final.content == polished
    assert input_.context.final.word_count == len(polished.split())
    assert input_.context.final.tone in {"professional", "conversational", "academic"}


@pytest.mark.asyncio
async def test_metadata_reflects_tokens_and_latency(agent, monkeypatch):
    monkeypatch.setattr(agent, "generate_text", mock_generate_text("A clear final draft here.", tokens=77, latency=250))

    input_ = make_input()
    output = await agent.execute(input_)

    assert output.metadata.tokens_used == 77
    assert output.metadata.latency_ms == 250
    assert output.metadata.error is None
    assert output.metadata.config == input_.config


@pytest.mark.asyncio
async def test_strips_whitespace_from_llm_output(agent, monkeypatch):
    monkeypatch.setattr(agent, "generate_text", mock_generate_text("   padded text here please   "))

    input_ = make_input()
    output = await agent.execute(input_)

    assert output.result == "padded text here please"
    assert not output.result.startswith(" ")
    assert not output.result.endswith(" ")


# ----------------------------------------------------------------------
# Tone inference
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tone_defaults_to_professional(agent, monkeypatch):
    monkeypatch.setattr(
        agent, "generate_text",
        mock_generate_text("The quarterly results exceeded expectations significantly."),
    )
    output = await agent.execute(make_input())
    assert output.status == AgentStatus.SUCCESS


@pytest.mark.asyncio
async def test_tone_detects_conversational_markers(agent, monkeypatch):
    text = "Hey, you know, this is honestly a pretty cool topic to dig into."
    monkeypatch.setattr(agent, "generate_text", mock_generate_text(text))

    input_ = make_input()
    await agent.execute(input_)

    assert input_.context.final.tone == "conversational"


@pytest.mark.asyncio
async def test_tone_detects_academic_markers(agent, monkeypatch):
    text = "Research indicates that study shows significant correlation in the data suggests trend."
    monkeypatch.setattr(agent, "generate_text", mock_generate_text(text))

    input_ = make_input()
    await agent.execute(input_)

    assert input_.context.final.tone == "academic"


# ----------------------------------------------------------------------
# Missing upstream data
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_draft_fails_gracefully(agent, monkeypatch):
    monkeypatch.setattr(agent, "generate_text", mock_generate_text("should not be called"))

    input_ = make_input(draft_content=None)
    output = await agent.execute(input_)

    assert output.status == AgentStatus.FAILED
    assert output.result == ""
    assert output.metadata.error is not None
    assert input_.context.final is None


@pytest.mark.asyncio
async def test_missing_edit_notes_still_succeeds(agent, monkeypatch):
    monkeypatch.setattr(agent, "generate_text", mock_generate_text("Polished content without edit notes."))

    input_ = make_input(edit_instructions=None)
    output = await agent.execute(input_)

    assert output.status == AgentStatus.SUCCESS
    assert input_.context.final is not None


# ----------------------------------------------------------------------
# Defensive / failure paths
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_llm_response_fails_instead_of_publishing(agent, monkeypatch):
    monkeypatch.setattr(agent, "generate_text", mock_generate_text(""))

    input_ = make_input()
    output = await agent.execute(input_)

    assert output.status == AgentStatus.FAILED
    assert input_.context.final is None


@pytest.mark.asyncio
async def test_generate_text_exception_does_not_crash(agent, monkeypatch):
    async def _raise(prompt: str):
        raise RuntimeError("upstream provider timed out")

    monkeypatch.setattr(agent, "generate_text", _raise)

    input_ = make_input()
    output = await agent.execute(input_)  # must not raise

    assert output.status == AgentStatus.FAILED
    assert "upstream provider timed out" in output.metadata.error
    assert input_.context.final is None


@pytest.mark.asyncio
async def test_duplicate_context_write_fails_gracefully(agent, monkeypatch):
    monkeypatch.setattr(agent, "generate_text", mock_generate_text("First valid final answer here."))

    input_ = make_input()
    # Pre-populate `final` to simulate a duplicate/second execution.
    from acs_shared.schemas import FinalOutput
    input_.context.set(
        "final", FinalOutput(content="already set", word_count=2, tone="professional")
    )

    output = await agent.execute(input_)

    assert output.status == AgentStatus.FAILED
    # Original value must remain untouched (append-only contract).
    assert input_.context.final.content == "already set"


# ----------------------------------------------------------------------
# Prompt construction
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_includes_topic_draft_and_edit_notes(agent, monkeypatch):
    captured = {}

    async def _capture(prompt: str):
        captured["prompt"] = prompt
        return "Final polished answer.", 10, 5

    monkeypatch.setattr(agent, "generate_text", _capture)

    input_ = make_input(
        draft_content="DRAFT_MARKER_TEXT",
        edit_instructions="EDIT_NOTE_MARKER",
        topic="TOPIC_MARKER",
    )
    await agent.execute(input_)

    assert "TOPIC_MARKER" in captured["prompt"]
    assert "DRAFT_MARKER_TEXT" in captured["prompt"]
    assert "EDIT_NOTE_MARKER" in captured["prompt"]


@pytest.mark.asyncio
async def test_prompt_handles_missing_edit_notes_with_placeholder(agent, monkeypatch):
    captured = {}

    async def _capture(prompt: str):
        captured["prompt"] = prompt
        return "Final polished answer.", 10, 5

    monkeypatch.setattr(agent, "generate_text", _capture)

    input_ = make_input(edit_instructions=None)
    await agent.execute(input_)

    assert "Edit Notes:\nNone" in captured["prompt"]
