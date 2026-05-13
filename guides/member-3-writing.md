# Member 3: Writing Agent Guide

## Your Role
You own the **Writing Agent** — the third pipeline stage. Your agent receives research + outline and must produce a full-length article. This is the core content generation stage.

## Your Files
| File | Purpose |
|---|---|
| `packages/agents/writing/agent.py` | **Your main file.** |
| `packages/agents/writing/server.py` | A2A server. |
| `prompts/writing.md` | Your system prompt. |

## Your Stage Output (`DraftOutput`)
```python
{
    'content': str,    # Full article text (1000-2500 words)
    'word_count': int, # len(content.split())
}
```

## Implementation
Your `context` has:
- `context.research` — summary, facts, sources
- `context.outline` — title, sections (headings + key points)

```python
prompt = self.load_prompt('writing')
full_prompt = f'''{prompt}

Topic: {input.topic}

Research Summary:
{input.context.research.summary}

Outline to follow:
{chr(10).join(f"## {s.heading}{chr(10)}" + chr(10).join(f"- {kp}" for kp in s.key_points) for s in input.context.outline.sections)}

Write the complete article now.'''
result, tokens, latency = await self.model.generate_with_metrics(
    prompt=full_prompt, config=input.config,
)
output = DraftOutput(content=result, word_count=len(result.split()))
```

## Key Rules
- Follow the outline **exactly** — one section per outline section, in order
- Use research facts — do not invent data or statistics
- Expand each outline section into 2-4 paragraphs
- Target 1000-2500 words
- Complete ALL sections — do not stop midway
- Use plain prose (no markdown headings or bullets in the final output)
