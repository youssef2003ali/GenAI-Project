# Member 5: Optimization Agent Guide

## Your Role
You own the **Optimization Agent** — the final pipeline stage. Your agent polishes the draft for tone, style, and clarity. **You must NOT shorten or summarize** — preserve all content, sections, and facts.

## Your Files
| File | Purpose |
|---|---|
| `packages/agents/optimization/agent.py` | **Your main file.** |
| `prompts/optimization.md` | Your polishing prompt. |

## Your Stage Output (`FinalOutput`)
```python
{
    'content': str,    # Polished article (90-110% of draft word count)
    'word_count': int,
    'tone': str,       # e.g., 'professional', 'academic', 'accessible'
}
```

## Critical Constraint
The `PipelineRunner` checks length preservation. Your output must be **90-110% of the draft word count**. If you shrink or expand beyond this, the pipeline logs a warning.

## Implementation
```python
prompt = self.load_prompt('optimization')
draft = input.context.draft
original_wc = draft.word_count
full_prompt = f'''{prompt}

Draft ({original_wc} words):
{draft.content}

Edit Scores: Coherence={input.context.edit.scores.coherence}/10,
             Relevance={input.context.edit.scores.relevance}/10,
             Completeness={input.context.edit.scores.completeness}/10
Feedback: {input.context.edit.instructions or "None"}

CRITICAL: Output must be between {int(original_wc * 0.9)} and {int(original_wc * 1.1)} words.
Do NOT add new content. Do NOT remove facts or sections.
Only improve: word choice, sentence rhythm, transitions, tone.'''
result, tokens, latency = await self.model.generate_with_metrics(
    prompt=full_prompt, config=input.config,
)
output = FinalOutput(content=result, word_count=len(result.split()), tone='professional')
```

## Polishing Rules
- Improve word choice: replace weak verbs, remove redundancy
- Improve sentence rhythm: vary sentence length, fix run-ons
- Improve transitions: add connecting phrases between paragraphs
- Preserve ALL: section headings, factual claims, examples, arguments
- Tone target: Professional but accessible. Match the topic's subject matter
- No meta-commentary — just the polished text
