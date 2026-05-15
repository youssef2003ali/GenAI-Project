# Member 4 — Editing Agent Implementation Guide

## Overview

The Editing Agent evaluates the draft on three quality dimensions (coherence, relevance, completeness) and decides whether it passes or needs a retry. This is the gatekeeper of content quality.

## Files You Own

| File | Purpose |
|------|---------|
| `packages/agents/editing/agent.py` | Your agent implementation |
| `packages/agents/editing/server.py` | A2A server (keep as-is) |
| `packages/agents/editing/pyproject.toml` | Dependencies |
| `prompts/editing.md` | Your prompt template |

## How It Works

```
AgentInput(topic, context) → EditingAgent.execute()
  → 1. Read context.draft from Writing Agent
  → 2. Load prompt from prompts/editing.md
  → 3. Call LLM via self.generate_text(prompt)
  → 4. Parse scores: coherence 0-10, relevance 0-10, completeness 0-10
  → 5. Calculate average
  → 6. If avg >= 7.0: status = SUCCESS (pass)
     If avg < 7.0: status = RETRY (improvement needed)
  → 7. input.context.set('edit', output)
  → AgentOutput(result, metadata, status)
```

## Required Schemas

```python
class EditScores(BaseModel):
    coherence: int      # 0-10
    relevance: int      # 0-10
    completeness: int   # 0-10

class EditOutput(BaseModel):
    scores: EditScores
    average: float
    passed: bool
    retry_count: int = 0
    instructions: str | None = None    # Improvement instructions on retry
```

## Implementation Steps

### Step 1: Read Draft
```python
draft_text = input.context.draft.content if input.context.draft else ''
```

### Step 2: Build Prompt
```python
prompt = self.load_prompt('editing')
prompt += f"""
Topic: {input.topic}
Draft:
{draft_text}

Score this draft on three dimensions (0-10):
- Coherence: logical flow and structure
- Relevance: stays on topic
- Completeness: covers all necessary points

Format your response exactly like:
Coherence: 8
Relevance: 7
Completeness: 9
Average: 8.0
Decision: PASS (or RETRY if avg < 7.0)
Issues: Specific improvement instructions if RETRY...
"""
```

### Step 3: Call LLM
```python
text, tokens, latency = await self.generate_text(prompt)
```

### Step 4: Parse Scores
Use `parse_edit_scores(text)` from `acs_shared.utils` as a starting point.

### Step 5: Track Retry Count
```python
retry_count = (input.context.edit.retry_count if input.context.edit else 0)
```

### Step 6: Return Decision
```python
status = AgentStatus.SUCCESS if passed else AgentStatus.RETRY
```

## Architecture Doc Rules

1. **Score on three dimensions**: coherence, relevance, completeness (0-10 each)
2. **If average < 7.0**: set `status: RETRY`, include specific improvement instructions
3. **Maximum 3 retries total** — after 3rd retry, pass forward regardless of score
4. **The Orchestrator's LoopAgent handles the retry cycle** — just return the right status
5. **Never hardcode model names** — read from input.config
6. **Always use `self.generate_text()`** — never call LLM SDK directly

## The Retry Loop

```
Pipeline → EditingAgent.execute()
  → RETRY (avg < 7.0)
  → LoopAgent re-runs: WritingAgent → EditingAgent
  → RETRY again...
  → Max 3 iterations → forced pass
```

## Testing

```bash
cd packages/agents
uv run adk web
# Select Editing Agent

uv run pytest tests/unit/test_editing.py -v
```
