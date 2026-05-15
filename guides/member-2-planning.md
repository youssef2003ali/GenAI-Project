# Member 2 — Planning Agent Implementation Guide

## Overview

The Planning Agent generates a structured outline from the research output. It creates 3-7 sections with key points, providing the blueprint for the Writing Agent.

## Files You Own

| File | Purpose |
|------|---------|
| `packages/agents/planning/agent.py` | Your agent implementation |
| `packages/agents/planning/server.py` | A2A server (keep as-is) |
| `packages/agents/planning/pyproject.toml` | Dependencies |
| `prompts/planning.md` | Your prompt template |

## How It Works

```
AgentInput(topic, context) → PlanningAgent.execute()
  → 1. Read context.research from previous agent
  → 2. Query LightRAG for additional context (Phase 2)
  → 3. Load prompt from prompts/planning.md
  → 4. Call LLM via self.generate_text(prompt)
  → 5. Parse LLM output → OutlineOutput
  → 6. input.context.set('outline', output)
  → AgentOutput(result, metadata, status)
```

## Required Schemas

```python
class OutlineSection(BaseModel):
    heading: str            # Section title
    key_points: list[str]   # 3-5 bullet points per section

class OutlineOutput(BaseModel):
    title: str              # Document title
    sections: list[OutlineSection]  # 3-7 sections
```

## Implementation Steps

### Step 1: Read Research
```python
research_summary = input.context.research.summary if input.context.research else ''
```

### Step 2: Query LightRAG (Phase 2)
```python
rag_context = await self.retrieve_from_memory(
    input.topic, mode='hybrid'
)
```

### Step 3: Build Prompt
```python
prompt = self.load_prompt('planning')
prompt += f"""
Topic: {input.topic}
Research Summary:
{research_summary}

Generate a structured outline with 4-6 sections.
Use ## for section headings and - for bullet points.
"""
```

### Step 4: Call LLM
```python
text, tokens, latency = await self.generate_text(prompt)
```

### Step 5: Parse Output
Parse the LLM output. The model typically returns:
```
## Section Title
- Key point 1
- Key point 2
- Key point 3
```

Parse `##` headings as `OutlineSection.heading` and `-` items as `key_points`.

### Step 6: Validate & Save
- Minimum 3 sections, maximum 7
- Each section must have at least 1 key point
- Save: `input.context.set('outline', output)`

## Architecture Doc Rules

1. **Must query LightRAG** with hybrid mode before generating outline
2. **Sections count: minimum 3, maximum 7** — no exceptions
3. **Never hardcode model names** — read from `input.config`
4. **Always use `self.generate_text()`** — never call LLM SDK directly

## Testing

```bash
cd packages/agents
uv run adk web
# Select Planning Agent

uv run pytest tests/unit/test_planning.py -v
```
