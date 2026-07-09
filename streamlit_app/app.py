"""Self-contained Streamlit frontend for the Agentic Content Generation System.

Runs the multi-agent pipeline inline (no separate backend needed).

Usage:
    streamlit run streamlit_app/app.py --server.port 8501
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
import uuid

import streamlit as st

# Ensure agent packages are importable
_AGENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'packages', 'agents')
if _AGENTS_PATH not in sys.path:
    sys.path.insert(0, _AGENTS_PATH)

from acs_shared.constants import AgentName, AgentStatus

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STAGES = [
    ('research',     '\U0001f50d', 'Research'),
    ('planning',     '\U0001f4cb', 'Planning'),
    ('writing',      '\u270d\ufe0f', 'Writing'),
    ('editing',      '\U0001f4dd', 'Editing'),
    ('optimization', '\u2728', 'Optimization'),
]

# ---------------------------------------------------------------------------
# Inline pipeline runner (runs in background thread)
# ---------------------------------------------------------------------------

def run_pipeline_inline(topic: str, state: dict, lock: threading.Lock) -> None:
    """Run the agent pipeline and write progress into ``state``."""
    async def _run():
        from orchestrator.pipeline import PipelineRunner
        from research.agent import ResearchAgent
        from planning.agent import PlanningAgent
        from writing.agent import WritingAgent
        from editing.agent import EditingAgent
        from optimization.agent import OptimizationAgent

        runner = PipelineRunner()
        runner.register_agent(AgentName.RESEARCH, ResearchAgent())
        runner.register_agent(AgentName.PLANNING, PlanningAgent())
        runner.register_agent(AgentName.WRITING, WritingAgent())
        runner.register_agent(AgentName.EDITING, EditingAgent())
        runner.register_agent(AgentName.OPTIMIZATION, OptimizationAgent())

        prev_agent = None

        async def _on_agent_complete(agent_name, output_text, ctx):
            nonlocal prev_agent
            agent = agent_name.value if hasattr(agent_name, 'value') else str(agent_name)
            with lock:
                if prev_agent and prev_agent != agent:
                    state['stage_status'][prev_agent] = 'completed'
                state['stage_status'][agent] = 'active'
                state['current_agent'] = agent
                state['stage_outputs'][agent] = output_text
            prev_agent = agent

        async def _on_chunk(agent_name, chunk, accumulated):
            agent = agent_name.value if hasattr(agent_name, 'value') else str(agent_name)
            with lock:
                state['stage_outputs'][agent] = accumulated

        try:
            ctx = await runner.run(
                job_id=state['job_id'], topic=topic,
                progress_callback=_on_agent_complete,
                chunk_callback=_on_chunk,
            )
            with lock:
                if prev_agent:
                    state['stage_status'][prev_agent] = 'completed'
                state['status'] = 'completed'
                state['final_output'] = ctx.final.content if ctx and ctx.final else ''
                state['context'] = ctx.model_dump() if ctx else {}
        except Exception as e:
            with lock:
                if prev_agent:
                    state['stage_status'][prev_agent] = 'failed'
                state['status'] = 'failed'
                state['error'] = str(e)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_research(raw: str | dict) -> str:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw.get('summary') or raw.get('raw') or str(raw)


def fmt_outline(raw: str | dict) -> str:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return raw
    title = raw.get('title', '')
    sections = raw.get('sections', [])
    lines = [f'# {title}', '']
    for s in sections:
        lines.append(f'## {s.get("heading", "")}')
        for kp in s.get('key_points', []):
            clean = str(kp).replace('```', '').strip('{}"\n ')
            if clean:
                lines.append(f'- {clean}')
        lines.append('')
    return '\n'.join(lines) or str(raw)


def fmt_writing(raw: str | dict) -> str:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw.get('content') or str(raw)


def fmt_editing(raw: str | dict) -> str:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return raw
    scores = raw.get('scores', {})
    lines = [
        f'**Coherence:** {scores.get("coherence", "-")}/10',
        f'**Relevance:** {scores.get("relevance", "-")}/10',
        f'**Completeness:** {scores.get("completeness", "-")}/10',
        f'**Average:** {raw.get("average", "-")}',
        f'**Passed:** {raw.get("passed", "-")}',
    ]
    if raw.get('instructions'):
        lines.append(f'\n**Feedback:** {raw["instructions"]}')
    return '\n\n'.join(lines)


def fmt_optimization(raw: str | dict) -> str:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw.get('content') or str(raw)


def format_agent_output(agent: str, raw: str | dict) -> str:
    formatters = {
        'research': fmt_research,
        'planning': fmt_outline,
        'writing': fmt_writing,
        'editing': fmt_editing,
        'optimization': fmt_optimization,
    }
    fn = formatters.get(agent)
    if fn:
        try:
            return fn(raw)
        except Exception:
            return str(raw)
    return str(raw)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title='Agentic Content System',
    page_icon='\U0001f916',
    layout='wide',
)

# Dark-theme custom CSS
st.markdown("""
<style>
.stage-row { display: flex; align-items: center; gap: 0.5rem; justify-content: center; flex-wrap: wrap; margin: 1rem 0; }
.stage-item { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; padding: 0.75rem 1rem; border-radius: 8px; background: #1e293b; border: 2px solid #475569; min-width: 90px; }
.stage-item.active { border-color: #f59e0b; background: rgba(245,158,11,0.1); }
.stage-item.completed { border-color: #22c55e; background: rgba(34,197,94,0.1); }
.stage-item.failed { border-color: #ef4444; background: rgba(239,68,68,0.1); }
.stage-icon { font-size: 1.5rem; }
.stage-label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.stage-arrow { color: #64748b; font-size: 1.25rem; }
.score-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; }
.score-item { display: flex; flex-direction: column; align-items: center; padding: 0.75rem 1.25rem; background: #1e293b; border-radius: 8px; min-width: 90px; }
.score-value { font-size: 1.5rem; font-weight: 700; }
.score-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)


def render_pipeline(stage_status: dict):
    """Render horizontal pipeline stage indicators."""
    n = len(STAGES)
    cols = st.columns(n * 2 - 1)
    idx = 0
    for i, (sid, icon, label) in enumerate(STAGES):
        with cols[idx]:
            s = stage_status.get(sid, 'pending')
            cls = 'stage-item'
            if s == 'active':
                cls += ' active'
            elif s == 'completed':
                cls += ' completed'
            elif s == 'failed':
                cls += ' failed'
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="stage-icon">{icon}</div>'
                f'<div class="stage-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        idx += 1
        if i < n - 1:
            with cols[idx]:
                st.markdown('<div class="stage-arrow">\u2192</div>', unsafe_allow_html=True)
            idx += 1


def render_edit_scores(edit: dict | None):
    if not edit:
        return
    scores = edit.get('scores', {}) if isinstance(edit, dict) else {}
    items = [
        ('Coherence', scores.get('coherence'), '#3b82f6'),
        ('Relevance', scores.get('relevance'), '#a855f7'),
        ('Completeness', scores.get('completeness'), '#22c55e'),
        ('Average', edit.get('average'), '#f59e0b'),
    ]
    st.markdown('---')
    st.markdown('**Edit Scores**')
    html = '<div class="score-row">'
    for label, val, color in items:
        display = str(val) if val is not None else '-'
        if isinstance(val, float):
            display = f'{val:.1f}'
        html += (
            f'<div class="score-item">'
            f'<div class="score-value" style="color:{color}">{display}</div>'
            f'<div class="score-label">{label}</div>'
            f'</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if 'job_id' not in st.session_state:
    st.session_state.job_id = None
if 'stage_status' not in st.session_state:
    st.session_state.stage_status = {s[0]: 'pending' for s in STAGES}
if 'stage_outputs' not in st.session_state:
    st.session_state.stage_outputs = {}
if 'final_output' not in st.session_state:
    st.session_state.final_output = None
if 'context' not in st.session_state:
    st.session_state.context = None
if 'status' not in st.session_state:
    st.session_state.status = 'idle'
if 'error' not in st.session_state:
    st.session_state.error = None
if 'thread' not in st.session_state:
    st.session_state.thread = None
if 'pipeline_state' not in st.session_state:
    st.session_state.pipeline_state = None
if 'pipeline_lock' not in st.session_state:
    st.session_state.pipeline_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title('\U0001f916 Agentic Content System')
st.caption('Ready' if not st.session_state.job_id else f'Job: {st.session_state.job_id[:8]}...')

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

with st.form('topic_form', clear_on_submit=False):
    topic = st.text_input(
        'Topic',
        placeholder='Enter a topic (e.g., Quantum Computing, Climate Change)...',
        disabled=st.session_state.status == 'running',
    )
    submitted = st.form_submit_button(
        'Generate Content',
        disabled=st.session_state.status == 'running',
        type='primary',
    )

# ---------------------------------------------------------------------------
# Start pipeline on submit
# ---------------------------------------------------------------------------

if submitted and topic:
    st.session_state.stage_status = {s[0]: 'pending' for s in STAGES}
    st.session_state.stage_outputs = {}
    st.session_state.final_output = None
    st.session_state.context = None
    st.session_state.status = 'running'
    st.session_state.error = None

    job_id = str(uuid.uuid4())
    st.session_state.job_id = job_id

    # Shared state dict the background thread writes to
    shared = {
        'job_id': job_id,
        'status': 'running',
        'current_agent': None,
        'stage_status': {s[0]: 'pending' for s in STAGES},
        'stage_outputs': {},
        'final_output': None,
        'context': None,
        'error': None,
    }
    st.session_state.pipeline_state = shared

    # Launch pipeline in background thread
    thread = threading.Thread(
        target=run_pipeline_inline,
        args=(topic, shared, st.session_state.pipeline_lock),
        daemon=True,
    )
    thread.start()
    st.session_state.thread = thread

    st.rerun()

# ---------------------------------------------------------------------------
# Poll pipeline state and update UI
# ---------------------------------------------------------------------------

if st.session_state.status == 'running':
    shared = st.session_state.pipeline_state
    if shared:
        lock = st.session_state.pipeline_lock
        with lock:
            # Copy latest from background thread
            st.session_state.stage_status = dict(shared.get('stage_status', {}))
            st.session_state.stage_outputs = dict(shared.get('stage_outputs', {}))
            new_status = shared.get('status', 'running')

        if new_status == 'completed':
            with lock:
                st.session_state.final_output = shared.get('final_output')
                st.session_state.context = shared.get('context')
            st.session_state.status = 'completed'
            st.session_state.thread = None
            st.rerun()
        elif new_status == 'failed':
            with lock:
                st.session_state.error = shared.get('error', 'Pipeline failed')
            st.session_state.status = 'failed'
            st.session_state.thread = None
            st.rerun()

    # Re-run after 2s to check again
    time.sleep(2)
    st.rerun()

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

render_pipeline(st.session_state.stage_status)

if st.session_state.error:
    st.error(st.session_state.error)

# Stage output expanders
if st.session_state.stage_outputs or st.session_state.context:
    st.markdown('### Agent Outputs')
    ctx = st.session_state.context or {}
    agent_map = {
        'research': ('research', '\U0001f50d Research'),
        'planning': ('outline', '\U0001f4cb Outline'),
        'writing': ('draft', '\u270d\ufe0f Draft'),
        'editing': ('edit', '\U0001f4dd Editing Scores'),
        'optimization': ('final', '\u2728 Final'),
    }
    for agent_id, (ctx_key, panel_title) in agent_map.items():
        raw = ctx.get(ctx_key)
        if not raw and agent_id in st.session_state.stage_outputs:
            raw = st.session_state.stage_outputs[agent_id]
        if raw:
            formatted = format_agent_output(agent_id, raw)
            with st.expander(panel_title, expanded=(agent_id == 'optimization')):
                st.markdown(formatted)

# Edit scores
edit = (st.session_state.context or {}).get('edit')
if edit:
    render_edit_scores(edit)

# Final output
if st.session_state.final_output:
    st.markdown('---')
    st.markdown('### \u2705 Final Output')
    st.markdown(st.session_state.final_output)
