# Member 1 — Research Agent Implementation Guide

## Overview

The Research Agent is responsible for:
1. Searching the web for information about the user's topic
2. Extracting full content from search results
3. Saving findings to LightRAG (knowledge memory)
4. Summarizing everything for downstream agents

## Files You Own

| File | Purpose |
|------|---------|
| `packages/agents/research/agent.py` | Your agent implementation |
| `packages/agents/research/server.py` | A2A server (keep as-is) |
| `packages/agents/research/tools/search.py` | Web search tool |
| `packages/agents/research/tools/scrape.py` | Content extraction tool |
| `packages/agents/research/pyproject.toml` | Dependencies |
| `prompts/research.md` | Your prompt template |

## How It Works

```
AgentInput(topic, context) → ResearchAgent.execute()
  → 1. Load prompt from prompts/research.md
  → 2. Open-WebSearch MCP: search the web for the topic
  → 3. Scrapling MCP: extract content from top 3-5 results
  → 4. Save findings to LightRAG via save_to_memory()
  → 5. Call LLM via self.generate_text(prompt)
  → 6. Parse LLM output → ResearchOutput
  → 7. input.context.set('research', output)
  → AgentOutput(result, metadata, status)
```

## Required Schemas

```python
class ResearchOutput(BaseModel):
    summary: str          # Concise summary of findings
    facts: list[str]       # 5+ key facts extracted
    sources: list[str]     # Source URLs / citations
    raw: str               # Full extracted content
```

## Implementation Steps

### Step 1: Web Search (MCP Tool)
The Open-WebSearch MCP is already wired in `agent.py` via `MCPToolset`. Use it to search:

```python
# The MCP tools are registered automatically — call them like this:
# (You need to add a tool call method to execute the MCP search)

# The tool is configured as:
MCPToolset(connection_params=StdioServerParameters(
    command='npx', args=['open-websearch@latest']
))
```

Search with the user's topic and get structured results (title, URL, description).

### Step 2: Content Extraction (MCP Tool)
Scrapling is already wired via MCP. Extract content from the top 3-5 search results:

```python
MCPToolset(connection_params=StdioServerParameters(
    command='python', args=['-m', 'scrapling.mcp']
))
```

### Step 3: Save to LightRAG
```python
await self.save_to_memory(
    text=extracted_content,
    metadata={'topic': input.topic, 'source': url}
)
```

### Step 4: Build Prompt
```python
prompt = self.load_prompt('research')
prompt += f"\n\nTopic: {input.topic}"
prompt += f"\n\nSearch Results:\n{formatted_results}"
```

### Step 5: Call LLM
```python
text, tokens, latency = await self.generate_text(prompt)
```

### Step 6: Parse Output
Parse the LLM response into a `ResearchOutput` with summary, facts, sources, and raw content.

### Step 7: Save to Context & Return
```python
output = ResearchOutput(summary=..., facts=[...], sources=[...], raw=...)
input.context.set('research', output)

return AgentOutput(
    job_id=input.job_id,
    agent=AgentName.RESEARCH,
    result=output.summary,
    metadata=AgentMetadata(config=input.config, tokens_used=tokens, latency_ms=latency),
    status=AgentStatus.SUCCESS,
)
```

## Architecture Doc Rules to Follow

1. **Must run Open-WebSearch MCP** before generating any output — no skipping
2. **Must run Scrapling** on top 3-5 search results to extract full content
3. **Must save all extracted findings** to LightRAG before returning
4. **Never call OpenRouter/Ollama/Mistral SDK directly** — always `self.generate_text()`
5. **Never hardcode model names** — read from `input.config`

## Testing

```bash
# Test your agent in isolation
cd packages/agents
uv run adk web
# Select Research Agent from dropdown

# Run unit tests
uv run pytest tests/unit/test_research.py -v
```
