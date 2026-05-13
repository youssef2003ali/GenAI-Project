# Member 2: Planning Agent Guide

## Your Role
You own the **Planning Agent** — the second pipeline stage. Your agent receives research output and must produce a structured outline. The Writing agent will follow your outline exactly, so quality here determines the entire article's structure.

## Your Files
| File | Purpose |
|---|---|
| `packages/agents/planning/agent.py` | **Your main file.** Replace Phase 1 dummy logic. |
| `packages/agents/planning/server.py` | A2A server. Do not modify. |
| `packages/agents/planning/Dockerfile` | Container config. |
| `packages/agents/planning/pyproject.toml` | Your dependencies. |
| `prompts/planning.md` | Your agent's system prompt. |

## Agent Contract

### Input
Your `context` will have `context.research` populated with `ResearchOutput`.

### Your Stage Output (`OutlineOutput`)
```python
{
    'title': str,                           # Article title
    'sections': list[OutlineSection] = [    # 5-8 sections recommended
        {'heading': str, 'key_points': list[str]},
        ...
    ],
}
```

### `OutlineSection`
```python
{
    'heading': str,          # Section title (e.g., "Key Challenges")
    'key_points': list[str], # 3-5 key points from research for this section
}
```

## Implementation

### Step 1: Replace Dummy Logic
```python
prompt = self.load_prompt('planning')
full_prompt = f'{prompt}\n\nResearch: {input.context.research.summary}\nTopic: {input.topic}'
result, tokens, latency = await self.model.generate_with_metrics(
    prompt=full_prompt, config=input.config,
)
# Parse LLM response into OutlineOutput sections
from acs_shared.utils import parse_outline
output = OutlineOutput(
    title=input.topic,
    sections=parse_outline(result),
)
```

### Parsing the Outline
The LLM returns something like:
```markdown
### 1. Introduction
- Context and background
- Why this matters

### 2. Main Analysis
- Key finding 1
- Key finding 2
```

Use `OutlineSection(heading=..., key_points=[...])` to structure it. The `parse_outline()` utility in `acs_shared.utils` handles `###`, `##`, `**bold**`, and numbered formats.

### Testing
```bash
uv run pytest tests/unit/test_planning.py -v
cd packages/agents && uv run adk web
```

### Rules
- **Always** base your outline on `context.research` — do not generate from the topic alone.
- Minimum 5 sections, maximum 8.
- Every section must have 3+ key points drawn from specific research facts.
- Return all sections in order — the writing agent follows them exactly.
