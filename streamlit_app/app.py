"""Streamlit frontend for the Agentic Content Generation System.

Usage:
    streamlit run streamlit_app/app.py --server.port 8501

Requires the backend running on port 8047 (or set API_BASE env var).
"""

import json
import os
import time
import urllib.parse

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE = os.getenv('API_BASE', 'http://localhost:8047')

STAGES = [
    ('research',     '\U0001f50d', 'Research'),
    ('planning',     '\U0001f4cb', 'Planning'),
    ('writing',      '\u270d\ufe0f', 'Writing'),
    ('editing',      '\U0001f4dd', 'Editing'),
    ('optimization', '\u2728', 'Optimization'),
]

AGENT_COLORS = {
    'research': '#3b82f6',
    'planning': '#a855f7',
    'writing': '#22c55e',
    'editing': '#f59e0b',
    'optimization': '#ef4444',
}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def submit_topic(topic: str) -> str:
    """POST /generate, return job_id."""
    resp = requests.post(
        f'{API_BASE}/generate',
        json={'topic': topic},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()['job_id']


def poll_job(job_id: str) -> dict:
    """GET /status/{job_id}. Returns status dict."""
    resp = requests.get(f'{API_BASE}/status/{job_id}', timeout=5)
    resp.raise_for_status()
    return resp.json()


def fetch_result(job_id: str) -> dict:
    """GET /result/{job_id}. Returns {status, final_output, context}."""
    resp = requests.get(f'{API_BASE}/result/{job_id}', timeout=10)
    resp.raise_for_status()
    return resp.json()

# ---------------------------------------------------------------------------
# Formatting helpers (mirrors Next.js extractAgentOutput)
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


def context_get(ctx: dict, key: str):
    """Safely get a key from context dict."""
    if not ctx:
        return None
    return ctx.get(key)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title='Agentic Content System',
    page_icon='\U0001f916',
    layout='wide',
)

# -- Dark theme by default --
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
    cols = st.columns(len(STAGES) * 2 - 1)
    col_idx = 0
    for i, (sid, icon, label) in enumerate(STAGES):
        with cols[col_idx]:
            status = stage_status.get(sid, 'pending')
            cls = 'stage-item'
            if status == 'active':
                cls += ' active'
            elif status == 'completed':
                cls += ' completed'
            elif status == 'failed':
                cls += ' failed'
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="stage-icon">{icon}</div>'
                f'<div class="stage-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        col_idx += 1
        if i < len(STAGES) - 1:
            with cols[col_idx]:
                st.markdown(
                    '<div class="stage-arrow">\u2192</div>',
                    unsafe_allow_html=True,
                )
            col_idx += 1


def render_edit_scores(edit: dict | None):
    """Render score cards when editing is done."""
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
# Session state init
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

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title('\U0001f916 Agentic Content System')

# -- Status badge --
if st.session_state.job_id:
    st.caption(f'Job: {st.session_state.job_id[:8]}...')
else:
    st.caption('Ready')

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
# Pipeline execution
# ---------------------------------------------------------------------------

if submitted and topic:
    # Reset state
    st.session_state.job_id = None
    st.session_state.stage_status = {s[0]: 'pending' for s in STAGES}
    st.session_state.stage_outputs = {}
    st.session_state.final_output = None
    st.session_state.context = None
    st.session_state.status = 'running'
    st.session_state.error = None

    try:
        job_id = submit_topic(topic)
        st.session_state.job_id = job_id
        st.caption(f'Job: {job_id[:8]}...')

        # Poll loop
        placeholder = st.empty()
        prev_agent = None

        while True:
            data = poll_job(job_id)
            s = data.get('status', 'unknown')

            if s == 'running':
                agent = data.get('current_agent')
                if agent and agent != prev_agent:
                    if prev_agent:
                        st.session_state.stage_status[prev_agent] = 'completed'
                    st.session_state.stage_status[agent] = 'active'
                    prev_agent = agent

            elif s == 'completed':
                if prev_agent:
                    st.session_state.stage_status[prev_agent] = 'completed'
                st.session_state.status = 'completed'

                result = fetch_result(job_id)
                st.session_state.final_output = result.get('final_output')
                st.session_state.context = result.get('context')
                break

            elif s == 'failed':
                if prev_agent:
                    st.session_state.stage_status[prev_agent] = 'failed'
                st.session_state.status = 'failed'
                st.session_state.error = data.get('progress', {}).get('error', 'Pipeline failed')
                break

            # Re-render pipeline
            with placeholder.container():
                render_pipeline(st.session_state.stage_status)

            time.sleep(2)

        # Final render after loop
        st.rerun()

    except requests.RequestException as e:
        st.session_state.status = 'failed'
        st.session_state.error = f'Connection error: {e}'
        st.rerun()

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

# Pipeline visualization
render_pipeline(st.session_state.stage_status)

# Error
if st.session_state.error:
    st.error(st.session_state.error)

# Stage output panels
if st.session_state.stage_outputs or st.session_state.context:
    st.markdown('### Agent Outputs')

    ctx = st.session_state.context or {}

    agent_map = {
        'research': ('research', '🔍 Research'),
        'planning': ('outline', '📋 Outline'),
        'writing': ('draft', '✍️ Draft'),
        'editing': ('edit', '📝 Editing Scores'),
        'optimization': ('final', '✨ Final'),
    }

    for agent_id, (ctx_key, panel_title) in agent_map.items():
        raw = context_get(ctx, ctx_key)
        if not raw and agent_id in st.session_state.stage_outputs:
            raw = st.session_state.stage_outputs[agent_id]
        if raw:
            formatted = format_agent_output(agent_id, raw)
            with st.expander(panel_title, expanded=(agent_id == 'optimization')):
                st.markdown(formatted)

# Edit scores
edit = context_get(st.session_state.context, 'edit')
if edit:
    render_edit_scores(edit)

# Final output
if st.session_state.final_output:
    st.markdown('---')
    st.markdown('### ✅ Final Output')
    st.markdown(st.session_state.final_output)
