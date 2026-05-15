# Member 5 — Optimization Agent Implementation Guide

## Overview

The Optimization Agent is the final step in the pipeline. It polishes the draft content — refining tone, style, and length — while preserving all factual content. The output is the final deliverable shown to the user.

## Files You Own

| File | Purpose |
|------|---------|
| `packages/agents/optimization/agent.py` | Your agent implementation |
| `packages/agents/optimization/server.py` | A2A server (keep as-is) |
| `packages/agents/optimization/pyproject.toml` | Dependencies |
| `prompts/optimization.md` | Your prompt template |

## How It Works

```
AgentInput(topic, context) → OptimizationAgent.execute()
  → 1. Read context.draft and context.edit from previous agents
  → 2. Load prompt from prompts/optimization.md
  → 3. Call LLM via self.generate_text(prompt) 
  → 4. Determine tone from content
  → 5. Create FinalOutput with word count
  → 6. input.context.set('final', output)
  → AgentOutput(result, metadata, status)
```

## Required Schemas

```python
class FinalOutput(BaseModel):
    content: str        # Clean, publishable content
    word_count: int     # Number of words
    tone: str           # e.g., 'professional', 'conversational', 'academic'
```

## Implementation Steps

### Step 1: Read Draft + Edit Notes
```python
draft_text = input.context.draft.content if input.context.draft else ''
edit_notes = input.context.edit.instructions if input.context.edit else ''
```

### Step 2: Build Prompt
```python
prompt = self.load_prompt('optimization')
prompt += f"""
Topic: {input.topic}
Draft:
{draft_text}
Edit Notes:
{edit_notes}

Polish this content: 
- Refine the tone (make it professional, clear, and engaging)
- Improve sentence flow and readability
- Preserve ALL factual content — do NOT change facts
- Keep the same structure and length
- Output clean, publishable text only
"""
```

### Step 3: Call LLM
```python
text, tokens, latency = await self.generate_text(prompt)
```

### Step 4: Determine Tone
```python
tone = 'professional'  # default
if any(w in text.lower() for w in ['you know', 'hey', 'well']):
    tone = 'conversational'
elif any(w in text.lower() for w in ['study shows', 'research indicates']):
    tone = 'academic'
```

### Step 5: Save & Return
```python
output = FinalOutput(content=text.strip(), word_count=len(text.split()), tone=tone)
input.context.set('final', output)

return AgentOutput(
    job_id=input.job_id,
    agent=AgentName.OPTIMIZATION,
    result=output.content,
    metadata=AgentMetadata(config=input.config, tokens_used=tokens, latency_ms=latency),
    status=AgentStatus.SUCCESS,
)
```

## Architecture Doc Rules

1. **Preserve ALL factual content** from the draft — no hallucinations
2. **Refine tone, style, and length only** — do not change substance
3. **Final output is clean, publishable content** — no metadata or scores in output
4. **Never hardcode model names** — read from `input.config`
5. **Always use `self.generate_text()`** — never call LLM SDK directly

## What "Polish" Means

| Do | Don't |
|----|-------|
| Improve sentence structure | Add new facts |
| Fix awkward phrasing | Remove existing facts |
| Adjust tone for audience | Change the outline structure |
| Fix grammar/spelling | Add opinions or commentary |
| Improve flow between paragraphs | Expand beyond original scope |

## Testing

```bash
cd packages/agents
uv run adk web
# Select Optimization Agent

uv run pytest tests/unit/test_optimization.py -v
```
