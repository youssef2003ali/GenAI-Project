# Agentic Content Generation System

A multi-agent pipeline built on Google ADK where specialized AI agents collaborate to autonomously generate high-quality content. A user submits a topic. Six agents handle the rest: research, planning, writing, editing, optimization, and orchestration.

## Architecture

```
Topic -> Research -> Planning -> Writing -> Editing -> Optimization -> Final Content
                        ^                                  |
                        +------- (max 3 retries) ----------+
```

## Team Structure

| Member | Agent | Responsibility | Guide |
|--------|-------|---------------|-------|
| Member 1 | Research Agent | Web search + content extraction via Open-WebSearch MCP and Scrapling | [guides/member-1-research.md](guides/member-1-research.md) |
| Member 2 | Planning Agent | Structured outline from research | [guides/member-2-planning.md](guides/member-2-planning.md) |
| Member 3 | Writing Agent | Full content generation from outline | [guides/member-3-writing.md](guides/member-3-writing.md) |
| Member 4 | Editing Agent | Quality scoring + retry decisions | [guides/member-4-editing.md](guides/member-4-editing.md) |
| Member 5 | Optimization Agent | Tone/style/length polishing | [guides/member-5-optimization.md](guides/member-5-optimization.md) |
| Member 6 | Orchestrator | System skeleton + pipeline coordination + infrastructure | Phase 1 complete ✅ |

## Tech Stack

- **Agent Framework**: Google ADK (Agent Development Kit)
- **Agent Communication**: A2A Protocol (Google/Linux Foundation)
- **LLM Provider**: OpenRouter (cloud), Ollama (local fine-tuned)
- **Knowledge Memory**: LightRAG (knowledge graph RAG)
- **Backend**: FastAPI + Redis + PostgreSQL
- **Frontend**: Next.js
- **MLOps**: MLflow
- **Deployment**: Docker Compose (Phase 1: Alibaba VPS, Phase 2: DatabaseMart VPS)
- **CI/CD**: GitHub Actions

## First Time Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop (optional, for containerized deployment)
- Git

### Quick Start (No Docker)

```bash
# 1. Clone the repo
git clone https://github.com/your-org/agentic-content-system
cd agentic-content-system

# 2. Install all dependencies via uv workspace
uv sync

# 3. Copy environment template
cp .env.example .env
# Edit .env - add your GEMINI_API_KEY for real AI agent calls
# Phase 1 dummy agents work without any API key

# 4. Install pre-commit hooks
uv run pre-commit install

# 5. Start the backend + frontend
uv run uvicorn packages.backend.main:app --host 0.0.0.0 --port 8000

# 6. Open the frontend
# Visit http://localhost:8000 in your browser
```

## Running the Web Interface

The frontend is a real-time dashboard built into the FastAPI backend:

```
http://localhost:8000
```

### How to Use

1. Open the dashboard in your browser
2. Enter a topic (e.g., "Quantum Computing", "Climate Change")
3. Click **Generate Content**
4. Watch the pipeline stages light up in real-time:
   - 🔍 Research → 📋 Planning → ✍️ Writing → 📝 Editing → ✨ Optimization
5. Each panel fills with output as agents complete
6. Final result appears with edit scores

> **Note:** Phase 1 uses dummy agents that return hardcoded data (no API key needed).
> For real AI-generated content, set `GEMINI_API_KEY` in `.env` and restart.
> The ADK + Gemini pipeline is pre-configured and tested.

### Architecture

```
Browser ──HTTP──> FastAPI ──BackgroundTask──> PipelineRunner
  │                                                  │
  └──── WebSocket <── QueueService <── stage updates ─┘
```

- `POST /generate` — submits topic, launches background pipeline
- `WS /ws/{job_id}` — streams real-time stage progress
- `GET /status/{job_id}` — polls current status
- `GET /result/{job_id}` — retrieves final output

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

# Integration test (full pipeline)
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

## Git Workflow

### Branch Strategy

- `main` — Production. Never push directly. PR only, 2 approvals required.
- `develop` — Integration branch. PR only, 1 approval required.
- `feature/your-agent` — Your personal branch. Push freely.

### Daily Workflow

```bash
# Pull latest
git checkout develop && git pull

# Switch to your feature branch
git checkout feature/your-agent

# Make changes and test
uv run pytest tests/unit/test_your_agent.py
uv run ruff check packages/agents/your-agent/

# Commit (pre-commit hooks run automatically)
git commit -m 'feat(agent): description of change'

# Push and open PR to develop
git push origin feature/your-agent
```

### Commit Convention

Format: `type(scope): description`
- Types: feat, fix, refactor, test, docs, chore, ci
- Scopes: research, planning, writing, editing, optimization, orchestrator, base, docker, ci, frontend

### Hard Rules

- Never push directly to main or develop
- Never force push
- Never modify another member's agent file
- Never modify shared/schemas.py without Member 6 approval
- Always open a Pull Request - never merge directly

## Project Structure

```
agentic-content-system/
├── pyproject.toml              # uv workspace root
├── .env.example                # Environment variable template
├── .pre-commit-config.yaml     # Pre-commit hooks
├── docker-compose.yml          # Phase 2 full stack
├── docker-compose.dev.yml      # Phase 1 minimal stack
├── Dockerfile.dev              # Dev container
├── nginx.conf                  # Reverse proxy config
├── packages/
│   ├── shared/                 # acs-shared - schemas, models, base agent
│   │   └── src/acs_shared/
│   │       ├── constants.py    # Provider, Model, AgentName, AgentStatus enums
│   │       ├── schemas.py      # All Pydantic schemas
│   │       ├── model.py        # AgentModel interface
│   │       ├── settings.py     # pydantic-settings from .env
│   │       ├── base_agent.py   # BaseAgent class
│   │       └── tools/          # LightRAG and MLflow tools
│   ├── agents/
│   │   ├── research/           # Member 1
│   │   ├── planning/           # Member 2
│   │   ├── writing/            # Member 3
│   │   ├── editing/            # Member 4
│   │   ├── optimization/       # Member 5
│   │   └── orchestrator/       # Member 6 - pipeline hub-spoke routing
│   └── backend/                # FastAPI backend
│       ├── main.py             # App entrypoint
│       ├── routers/            # REST + WebSocket routes
│       ├── services/           # Redis, LightRAG, MLflow clients
│       └── db/                 # Database models
├── prompts/                    # Agent prompt templates
│   ├── research.md
│   ├── planning.md
│   ├── writing.md
│   ├── editing.md
│   └── optimization.md
├── tests/                      # Unit + integration tests
│   ├── conftest.py             # Shared fixtures
│   ├── unit/                   # Per-agent unit tests
│   └── integration/            # End-to-end pipeline test
├── frontend/                   # Next.js UI (placeholder)
├── lightrag/                   # LightRAG service (placeholder)
├── monitoring/                 # Prometheus + Grafana config
└── .github/workflows/          # CI/CD pipelines
    ├── pr.yml                  # Runs on every PR to develop
    ├── develop.yml             # Runs on merge to develop
    └── main.yml                # Runs on merge to main
```

## Development Phases

| Phase | Timeline | Focus |
|-------|----------|-------|
| Phase 1 | Weeks 1-2 | **Skeleton**: uv workspace, shared package, dummy agents, FastAPI, Docker, CI/CD |
| Phase 2 | Weeks 3-5 | **Agent Development**: Real agent logic with OpenRouter cloud models |
| Phase 3 | Weeks 5-6 | **Integration & Evaluation**: Retry loop testing, MLflow, Prometheus |
| Phase 4 | Weeks 7-8 | **Full Deployment**: DatabaseMart VPS, all 11 containers, SSL, auto-deploy |
| Phase 5 | Weeks 9-10 | **Fine-tuning**: Local models via Ollama, cloud/local swap |
| Phase 6 | Week 10 | **Final Report & Presentation**: Documentation, demo, report |

## Agent Contract

Every agent receives the same input and returns the same output structure:

### Input
```python
job_id    # unique job ID
topic     # the topic to generate content about
context   # PipelineContext with all previous agent outputs
config    # which model to use
```

### Output
```python
job_id    # same ID received
agent     # agent name (e.g. 'writing')
result    # output as JSON string
metadata  # dict: model, tokens_used, latency_ms, retry_count
status    # 'success', 'retry', or 'failed'
```

### Rules
- Always return AgentOutput with all fields filled
- Always use self.model.generate() to call the LLM
- Always read previous outputs from input.context
- Never call OpenRouter or any LLM SDK directly
- Never hardcode model names - read from input.config
- Never crash - catch all errors and return status: failed

## Questions?

Ask Member 6 (Orchestrator) first. Try ADK Web debugging before asking.
The detailed architecture document has the full picture.
