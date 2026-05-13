# Member 1: Research Agent Guide

## Your Role
You own the **Research Agent** — the first stage in the pipeline. Your agent receives a topic and must produce a structured research output with summary, facts, sources, and raw content. Everything downstream depends on your output quality.

## Your Files

| File | Purpose |
|---|---|
| `packages/agents/research/agent.py` | **Your main file.** Replace the Phase 1 dummy logic with real LLM calls. |
| `packages/agents/research/server.py` | A2A server for ADK Web. **Do not modify** unless adding endpoints. |
| `packages/agents/research/tools/` | Your tools directory. Add web search, scraping, or RAG tools here. |
| `packages/agents/research/Dockerfile` | Container config. Modify if you add system dependencies. |
| `packages/agents/research/pyproject.toml` | Your dependencies. Add packages with `uv add --active`. |
| `prompts/research.md` | Your agent's system prompt template. |

## Agent Contract

Every agent receives the same input and returns the same output structure:

### Input (`AgentInput`)
```python
{
    'job_id': str,      # Unique job ID for tracing
    'topic': str,       # The topic to research
    'context': PipelineContext,  # All previous agents' outputs (None for you)
    'config': AgentConfig,       # Model provider, name, temperature, max_tokens
}
```

### Output (`AgentOutput`)
```python
{
    'job_id': str,
    'agent': AgentName.RESEARCH,
    'result': str,       # JSON string of your ResearchOutput
    'metadata': {
        'config': AgentConfig,
        'tokens_used': int,
        'latency_ms': int,
        'retry_count': int,
        'error': str | None,
    },
    'status': AgentStatus,  # SUCCESS | RETRY | FAILED
}
```

### Your Stage Output (`ResearchOutput`)
```python
{
    'summary': str,       # Comprehensive research summary
    'facts': list[str],   # Extracted factual statements (use extract_facts())
    'sources': list[str], # Academic/professional sources (use parse_sources())
    'raw': str,           # Full raw research content
}
```

## How to Implement Your Agent

### Step 1: Replace Phase 1 Dummy Logic
Open `packages/agents/research/agent.py`. The current dummy:
```python
output = ResearchOutput(
    summary=f'Research findings about: {input.topic}',
    facts=['Fact 1: ...', 'Fact 2: ...'],
    sources=['https://example.com/source1'],
    raw='Raw extracted content...',
)
```

Replace with real LLM calls using `self.model.generate()`:
```python
prompt = self.load_prompt('research')
full_prompt = f'{prompt}\n\nTopic: {input.topic}'
result, tokens, latency = await self.model.generate_with_metrics(
    prompt=full_prompt,
    config=input.config,
)
# Parse the LLM response into ResearchOutput
from acs_shared.utils import extract_facts, parse_sources
output = ResearchOutput(
    summary=result,
    facts=extract_facts(result),
    sources=parse_sources(result),
    raw=result,
)
```

### Step 2: Add Tools
In `packages/agents/research/tools/`, add tools for:
- **Web search**: Use the Open-WebSearch MCP (configured in your environment)
- **Web scraping**: Use Scrapling (listed in the tech stack)
- **LightRAG**: Use `self.save_to_memory()` and `self.retrieve_from_memory()` for knowledge persistence

### Step 3: Test Your Agent
```bash
# Unit test
uv run pytest tests/unit/test_research.py -v

# Run in isolation via ADK Web
cd packages/agents
uv run adk web
# Select your agent from the dropdown, send test inputs

# Test the full pipeline
uv run pytest tests/integration/test_pipeline.py -v
```

### Step 4: Commit Your Work
```bash
git checkout -b feature/research-agent
git add packages/agents/research/
git commit -m 'feat(research): implement real LLM research agent with web search'
git push origin feature/research-agent
# Open PR to develop
```

## Available Utilities (in `acs_shared`)

- `extract_facts(text)` — Extracts factual sentences, filters out headings
- `parse_sources(text)` — Extracts academic citations from text
- `parse_edit_scores(text)` — If you get edit feedback to incorporate
- `BaseAgent.load_prompt(name)` — Loads prompt from `prompts/{name}.md`
- `BaseAgent.save_to_memory(text)` — Save to LightRAG (Phase 1: no-op)
- `BaseAgent.retrieve_from_memory(query)` — Retrieve from LightRAG (Phase 1: empty)

## Rules
- **Never** call OpenRouter, Ollama, or any LLM SDK directly. Always use `self.model.generate()`.
- **Never** hardcode model names. Read from `input.config.model`.
- **Never** crash. Catch errors and return `status: AgentStatus.FAILED` with a descriptive error message.
- **Never** modify `packages/shared/` schemas without approval from Member 6.
- **Always** set `input.context.set('research', output)` at the end of your execute method.

## Git Workflow
- Branch from `develop`: `git checkout -b feature/research-agent`
- Commit convention: `feat(research): description`
- Push and open PR to `develop` — never merge directly
- Pre-commit hooks will lint + format your code automatically
