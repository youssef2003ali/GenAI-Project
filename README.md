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

> **Current status:** Agents are stubbed with implementation guides. Each member implements their agent's `execute()` method in `packages/agents/<name>/agent.py`.

## Tech Stack

- **Agent Framework**: Google ADK (Agent Development Kit)
- **LLM Abstraction**: LiteLLM (supports Mistral, OpenRouter, Gemini, Ollama, 100+ providers)
- **Current Provider**: Mistral AI (`mistral-large-latest`)
- **Pipeline**: ADK SequentialAgent + LoopAgent
- **Agent Communication**: A2A Protocol (each agent runs as an A2A server)
- **Knowledge Memory**: LightRAG (knowledge graph RAG) — Phase 2
- **Backend**: FastAPI + Redis + PostgreSQL
- **Frontend**: Next.js 14 + React 18
- **MLOps**: MLflow
- **Deployment**: Docker Compose (11 containers)
- **CI/CD**: GitHub Actions
- **Code Quality**: Ruff (lint + format), pre-commit hooks

## First Time Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend)
- Docker Desktop (optional)

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/agentic-content-system
cd agentic-content-system

# 2. Install all dependencies via uv workspace
uv sync

# 3. Copy and configure environment
cp .env.example .env
# Edit .env — add your MISTRAL_API_KEY for real AI agent calls
# The system works without an API key (uses dummy fallback for dev)

# 4. Install pre-commit hooks
uv run pre-commit install

# 5. Start backend
uv run uvicorn packages.backend.main:app --host 0.0.0.0 --port 8000

# 6. In another terminal, start frontend
cd frontend && npm run dev

# 7. Open http://localhost:3000 in your browser
```

### Environment Configuration

```env
# Required for real AI content
MISTRAL_API_KEY=your-mistral-api-key

# Optional: per-agent model overrides
RESEARCH_MODEL=mistral-large-latest
PLANNING_MODEL=mistral-large-latest
WRITING_MODEL=mistral-large-latest
EDITING_MODEL=mistral-large-latest
OPTIMIZATION_MODEL=mistral-small-latest
```

### How to Use

1. Enter a topic (e.g., "Quantum Computing", "Climate Change")
2. Click **Generate Content**
3. Watch the 5 pipeline stages light up in real-time:
   - 🔍 Research → 📋 Planning → ✍️ Writing → 📝 Editing → ✨ Optimization
4. Each panel fills with output as agents complete
5. Final result appears with edit scores

> **Note:** Without a `MISTRAL_API_KEY`, agents return dummy fallback text. This is useful for frontend development and pipeline testing without consuming API quota.

### API Endpoints

```
GET  /health              → Health check
GET  /agents/status       → Agent availability
POST /generate            → Submit topic, returns job_id
GET  /status/{job_id}     → Poll pipeline progress
GET  /result/{job_id}     → Get final output
WS   /ws/{job_id}         → Real-time streaming updates
```

## Running with Docker

```bash
# Phase 1 dev stack (backend + Redis)
docker compose -f docker-compose.dev.yml up -d

# Verify
curl http://localhost:8000/health
```

## Run Tests

```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# Specific agent test
uv run pytest tests/unit/test_research.py -v

# Full pipeline integration test
uv run pytest tests/integration/ -v
```

### Develop Your Agent with ADK Web

```bash
cd packages/agents
uv run adk web
# Opens browser at http://localhost:8000
# Select your agent from the dropdown
# Send test inputs and inspect outputs interactively
```

## Project Structure

```
agentic-content-system/
├── pyproject.toml              # uv workspace root
├── .env.example                # Environment variable template
├── .pre-commit-config.yaml     # Pre-commit hooks
├── docker-compose.yml          # Full stack (11 containers)
├── docker-compose.dev.yml      # Dev stack (backend + Redis)
├── Dockerfile.dev              # Dev container
├── nginx.conf                  # Reverse proxy
├── run_backend.py              # Backend launcher script
├── packages/
│   ├── shared/                 # acs-shared — schemas, models, base agent
│   │   └── src/acs_shared/
│   │       ├── constants.py    # Provider/Model/AgentName/AgentStatus enums
│   │       ├── schemas.py      # All Pydantic schemas (AgentInput, PipelineContext, etc.)
│   │       ├── model.py        # AgentModel via LiteLLM (provider-agnostic)
│   │       ├── settings.py     # pydantic-settings from .env
│   │       ├── base_agent.py   # BaseAgent class (prompt loading, MLflow, metrics)
│   │       └── tools/          # LightRAG + MLflow tool stubs
│   ├── agents/
│   │   ├── research/           # Member 1 — stub + guide
│   │   ├── planning/           # Member 2 — stub + guide
│   │   ├── writing/            # Member 3 — stub + guide
│   │   ├── editing/            # Member 4 — stub + guide
│   │   ├── optimization/       # Member 5 — stub + guide
│   │   └── orchestrator/       # Member 6 — ADK pipeline (complete)
│   │       ├── pipeline.py     # PipelineRunner → delegates to ADK
│   │       └── adk_runner.py   # ADK SequentialAgent + LoopAgent orchestration
│   └── backend/                # FastAPI backend
│       ├── main.py             # App entrypoint
│       ├── routers/            # REST + WebSocket routes
│       ├── services/           # Redis queue, LightRAG, MLflow clients
│       └── db/                 # Database models
├── prompts/                    # Agent prompt templates
├── tests/                      # Unit + integration tests
├── frontend/                   # Next.js 14 React app
├── guides/                     # Per-agent implementation guides
├── monitoring/                 # Prometheus + Grafana
└── .github/workflows/          # CI/CD pipelines
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
