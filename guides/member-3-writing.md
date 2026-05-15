# Member 3 — Writing Agent Implementation Guide

## Overview

The Writing Agent generates full prose content from the outline produced by the Planning Agent. It must follow the outline structure exactly and produce 500-2000 words of clean, readable content.

## Files You Own

| File | Purpose |
|------|---------|
| `packages/agents/writing/agent.py` | Your agent implementation |
| `packages/agents/writing/server.py` | A2A server (keep as-is) |
| `packages/agents/writing/pyproject.toml` | Dependencies |
| `prompts/writing.md` | Your prompt template |

## How It Works

```
AgentInput(topic, context) → WritingAgent.execute()
  → 1. Read context.outline from Planning Agent
  → 2. Query LightRAG for additional context (Phase 2)
  → 3. Load prompt from prompts/writing.md
  → 4. Call LLM via self.generate_text(prompt)
  → 5. Create DraftOutput with word count
  → 6. input.context.set('draft', output)
  → AgentOutput(result, metadata, status)
```

## Required Schemas

```python
class DraftOutput(BaseModel):
    content: str        # Full prose content
    word_count: int     # Number of words
```

## Implementation Steps

### Step 1: Read Outline
```python
outline = input.context.outline
# Build a text representation
outline_text = ''
for section in outline.sections:
    outline_text += f"### {section.heading}\n"
    for point in section.key_points:
        outline_text += f"- {point}\n"
```

### Step 2: Query LightRAG (Phase 2)
```python
rag_context = await self.retrieve_from_memory(
    input.topic, mode='hybrid'
)
```

### Step 3: Build Prompt
```python
prompt = self.load_prompt('writing')
prompt += f"""
Topic: {input.topic}
Outline:
{outline_text}

Write a full article following the outline above.
Expand each section into 2-3 paragraphs of clean prose.
Do NOT use markdown headers or bullet points in the output.
"""
```

### Step 4: Call LLM
```python
text, tokens, latency = await self.generate_text(prompt)
```

### Step 5: Validate Word Count
```python
word_count = len(text.split())
# Must be 500-2000 words
```

## Architecture Doc Rules

1. **Must query LightRAG** before generating — use outline from context
2. **Must follow the outline structure exactly** — do not invent new sections
3. **Output must be clean prose** — no markdown headers, no bullet points
4. **Minimum 500 words, maximum 2000 words**
5. **Never hardcode model names** — read from `input.config`
6. **Always use `self.generate_text()`** — never call LLM SDK directly

## Retry Loop

The Editing Agent may return `RETRY` if scores are below 7.0. When this happens:
- The Orchestrator's LoopAgent clears `context.draft` and re-runs you
- You will see `input.context.edit.instructions` with improvement feedback
- Read the feedback and rewrite accordingly
- Maximum 3 retries total

## Testing

```bash
cd packages/agents
uv run adk web
# Select Writing Agent

uv run pytest tests/unit/test_writing.py -v
```
