# Member 4: Editing Agent Guide

## Your Role
You own the **Editing Agent** — the quality gate. Your agent evaluates the draft against the research and outline, scoring it on three dimensions. You decide PASS or RETRY. When you return RETRY, the pipeline loops back to Writing (max 3 retries) with your instructions.

## Your Files
| File | Purpose |
|---|---|
| `packages/agents/editing/agent.py` | **Your main file.** |
| `prompts/editing.md` | Your scoring rubric prompt. |

## Your Stage Output (`EditOutput`)
```python
{
    'scores': EditScores(coherence=int, relevance=int, completeness=int),
    'average': float,       # (coherence + relevance + completeness) / 3
    'passed': bool,         # True if avg >= 7.0
    'retry_count': int,     # Read from context.edit.retry_count if exists
    'instructions': str | None,  # Specific improvement instructions for retry
}
```

## Scoring Rubric

| Dimension | What to Check |
|---|---|
| **Coherence** (0-10) | Logical flow, transitions between sections, paragraph structure |
| **Relevance** (0-10) | Every paragraph relates to the topic and outline section |
| **Completeness** (0-10) | ALL outline sections covered with adequate depth |

## Implementation
```python
prompt = self.load_prompt('editing')
full_prompt = f'''{prompt}

Research Facts: {input.context.research.facts}
Outline: {[s.heading for s in input.context.outline.sections]}
Draft: {input.context.draft.content}
Word Count: {input.context.draft.word_count}

Score each dimension out of 10 with specific justification.'''
result, tokens, latency = await self.model.generate_with_metrics(
    prompt=full_prompt, config=input.config,
)
from acs_shared.utils import parse_edit_scores
scores = parse_edit_scores(result)
output = EditOutput(
    scores=EditScores(**scores),
    average=scores['average'],
    passed=scores['passed'],
    retry_count=(input.context.edit.retry_count if input.context.edit else 0) + 1,
    instructions=scores.get('issues'),
)
```

## Retry Flow
- If `avg >= 7.0`: Set `passed=True`, pipeline proceeds to Optimization
- If `avg < 7.0`: Set `passed=False`, return `status=AgentStatus.RETRY`
  - Pipeline resets `context.draft` + `context.edit` and re-runs Writing → Editing
  - Your `instructions` tell Writing what to fix
  - Max 3 retries
- **Never give 10/10** — there are always improvements
- Be specific: quote sentences, cite missing sections
