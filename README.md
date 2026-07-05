# Agentic Content Generation System

A multi-agent pipeline built on **Google ADK** where specialized AI agents collaborate to autonomously generate high-quality content. A user submits a topic. Six agents handle the rest: research, planning, writing, editing, optimization, and orchestration.

All LLM calls route through **LiteLLM**, providing a unified interface to Mistral AI, OpenRouter, Gemini, and 100+ providers. Currently configured with **Mistral AI** as the primary provider.

## Architecture

```
                                   ┌─────────────────────────┐
                                   │   ADK SequentialAgent   │
Topic ──► Research ──► Planning ──┤                         ├──► Optimization ──► Final
                                   │   ┌─────────────────┐  │
                                   │   │  LoopAgent x3   │  │
                                   │   │ Writing ◄──► Edit│  │
                                   │   └─────────────────┘  │
                                   └─────────────────────────┘
```

- **SequentialAgent** runs agents in strict order
- **LoopAgent** handles the Editing → Writing retry cycle (max 3 iterations)
- Editing returns `RETRY` → pipeline re-runs Writing → Editing
- Editing returns `SUCCESS` → pipeline continues to Optimization

## Team Structure

| Member | Agent | Responsibility | Guide |
|--------|-------|---------------|-------|
| Member 1 | Research Agent | Web search + content extraction via Open-WebSearch MCP and Scrapling | [guide](guides/member-1-research.md) |
| Member 2 | Planning Agent | Structured outline from research (3-7 sections) | [guide](guides/member-2-planning.md) |
| Member 3 | Writing Agent | Full content generation from outline (500-2000 words) | [guide](guides/member-3-writing.md) |
| Member 4 | Editing Agent | Quality scoring (coherence, relevance, completeness) + retry decisions | [guide](guides/member-4-editing.md) |
| Member 5 | Optimization Agent | Tone/style/length polishing | [guide](guides/member-5-optimization.md) |
| Member 6 | Orchestrator | ADK pipeline coordination + infrastructure | ✅ Complete |

> **Current status:** Orchestrator, pipeline infrastructure, and shared agent contracts are complete. Individual agents are in active implementation by team members. Each member implements their agent's `execute()` method in `packages/agents/<name>/agent.py`.

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+

### 1. Install dependencies

```powershell
uv sync
cd frontend
npm install
cd ..
```

### 2. Configure API key

Copy `.env.example` to `.env` and add your Mistral API key:

```powershell
copy .env.example .env
# Edit .env — set MISTRAL_API_KEY=your-key
```

### 3. Fix Windows `npx` resolution (one-time)

`packages/agents/research/tools/search.py` line 33 — change `npx` to `npx.cmd`:

```powershell
uv run python -c "path = r'packages\agents\research\tools\search.py'; content = open(path).read(); open(path, 'w').write(content.replace(\"command='npx'\", \"command='npx.cmd'\"))"
```

### 4. Start backend (Terminal 1)

```powershell
uv run uvicorn packages.backend.main:app --host 0.0.0.0 --port 8047
```

### 5. Start frontend (Terminal 2)

```powershell
cd frontend
npm run dev
```

### 6. Use it

Open `http://localhost:3047` — enter a topic, click generate.

### Environment

```env
MISTRAL_API_KEY=your-key              # Required
RESEARCH_MODEL=mistral-large-latest    # Optional overrides
WRITING_MODEL=mistral-large-latest
```

### Verify with curl

```powershell
Invoke-WebRequest -Uri "http://localhost:8047/health"
Invoke-WebRequest -Uri "http://localhost:8047/generate" -Method POST -ContentType "application/json" -Body '{"topic":"Quantum Computing"}'
```

## Run Tests

```powershell
uv run pytest tests/ -v
```

## Project Structure

```
packages/
├── shared/src/acs_shared/     # Schemas, base agent, LiteLLM model
├── agents/
│   ├── research/              # Web search + scrape (MCP)
│   ├── planning/              # Outline from research
│   ├── writing/               # Full article from outline
│   ├── editing/               # Score + retry decision
│   ├── optimization/          # Final polish
│   └── orchestrator/          # ADK pipeline runner
├── backend/                   # FastAPI + WebSocket
└── frontend/                  # Next.js UI
```

## Agent Contract

Every agent receives the same input and returns the same output structure:

### Input
```
job_id    unique job ID
topic     the topic to generate content about
context   PipelineContext with all previous agent outputs
config    which model/provider to use
```

### Output
```
job_id    same ID received
agent     agent name (e.g. 'writing')
result    text output
metadata  model, tokens_used, latency_ms, retry_count
status    'success', 'retry', or 'failed'
```

### Rules
- Always return `AgentOutput` with all fields filled
- Always use `self.generate_text()` — never call LLM SDKs directly
- Never hardcode model names — read from `input.config`
- Never crash — catch all errors and return `status: failed`
- Context is append-only (`context.set()` raises on duplicate)

## Developing Your Agent

Each member has a stub agent file and a detailed guide:

| Member | Stub File | Guide |
|--------|-----------|-------|
| 1 — Research | `packages/agents/research/agent.py` | [guides/member-1-research.md](guides/member-1-research.md) |
| 2 — Planning | `packages/agents/planning/agent.py` | [guides/member-2-planning.md](guides/member-2-planning.md) |
| 3 — Writing | `packages/agents/writing/agent.py` | [guides/member-3-writing.md](guides/member-3-writing.md) |
| 4 — Editing | `packages/agents/editing/agent.py` | [guides/member-4-editing.md](guides/member-4-editing.md) |
| 5 — Optimization | `packages/agents/optimization/agent.py` | [guides/member-5-optimization.md](guides/member-5-optimization.md) |

Each stub contains:
- Class definition extending `BaseAgent`
- `execute()` method skeleton with `# --- YOUR CODE HERE ---` marker
- Detailed docstring with step-by-step implementation instructions
- Correct schema imports and method signatures

## Git Workflow

### Branch Strategy

- `main` — Production. PR only, 2 approvals required.
- `develop` — Integration branch. PR only, 1 approval required.
- `feature/your-agent` — Your personal branch. Push freely.

### Commit Convention

Format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`
- Scopes: `research`, `planning`, `writing`, `editing`, `optimization`, `orchestrator`, `base`, `docker`, `ci`, `frontend`

### Hard Rules

- Never push directly to main or develop
- Never force push
- Never modify another member's agent file
- Never modify `shared/schemas.py` without Member 6 approval
- Always open a Pull Request — never merge directly
- Never import an LLM SDK directly — always use `self.generate_text()`
