"""ADK + Gemini pipeline runner. Wires Google ADK agents into the PipelineRunner.

Uses Gemini 2.5 Flash when GEMINI_API_KEY is set in .env.
Falls back to Phase 1 dummy agents when no API key is available.
"""

import logging
import os
import sys
import re

logger = logging.getLogger(__name__)

# Ensure agent packages are importable
_AGENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')
if _AGENTS_PATH not in sys.path:
    sys.path.insert(0, _AGENTS_PATH)

from acs_shared.schemas import (
    ResearchOutput, OutlineSection, OutlineOutput, DraftOutput,
    EditOutput, EditScores, FinalOutput, AgentOutput, AgentMetadata,
)
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.base_agent import BaseAgent as ACSBaseAgent
from acs_shared.settings import settings
from orchestrator.pipeline import PipelineRunner


def _has_gemini_key() -> bool:
    return bool(settings.gemini_api_key) and len(settings.gemini_api_key) > 10


# ── ADK imports (lazy — only when API key available) ──
_ADK_IMPORTED = False
AdkAgent = None
AdkRunner = None
InMemorySessionService = None
genai_types = None


def _ensure_adk():
    global _ADK_IMPORTED, AdkAgent, AdkRunner, InMemorySessionService, genai_types
    if not _ADK_IMPORTED:
        from google.adk.agents import Agent as _Agent
        from google.adk.runners import Runner as _Runner
        from google.adk.sessions import InMemorySessionService as _SessionService
        from google.genai import types as _types
        AdkAgent = _Agent
        AdkRunner = _Runner
        InMemorySessionService = _SessionService
        genai_types = _types
        _ADK_IMPORTED = True


# ── Utility functions ──
def extract_facts(text: str, max_facts: int = 8) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    facts = []
    for s in sentences:
        s = s.strip()
        if not s or len(s) < 30: continue
        if re.match(r'^#', s): continue
        if re.match(r'^[*\-]\s', s): continue
        if re.match(r'^\d+[\.\)]\s', s): continue
        if s.startswith('http') or s.startswith('---'): continue
        if any(kw in s.lower() for kw in [
            ' is ', ' was ', ' are ', ' were ', ' has ', ' have ',
            'discovered', 'developed', 'created', 'found ',
            'demonstrated', 'consists', 'contains',
            'measured', 'estimated', 'according',
            'percent', '%', 'million', 'billion',
            'years', 'century', '19', '20', '202',
        ]):
            clean = s.lstrip('*#- ').strip()
            if clean not in facts: facts.append(clean[:300])
            if len(facts) >= max_facts: break
    return facts if facts else [text[:200]]


def parse_sources(text: str) -> list[str]:
    sources = []
    lines = text.split('\n')
    in_block = False
    for line in lines:
        s = line.strip()
        if not s: continue
        if re.match(r'^#{1,3}\s*(Sources?|References?|Bibliography)', s, re.IGNORECASE):
            in_block = True; continue
        if in_block and re.match(r'^#{1,3}\s', s): in_block = False; continue
        if in_block:
            if re.match(r'^\d+[\.\)]\s', s) or re.match(r'^[*\-]\s', s):
                clean = re.sub(r'^\d+[\.\)]\s*', '', s)
                clean = re.sub(r'^[*\-]\s*', '', clean)
                if clean and len(clean) > 20 and clean not in sources: sources.append(clean[:300])
    if not sources:
        citations = re.findall(r'\([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+))?\s*,\s*\d{4}\)', text)
        for c in citations:
            if c not in sources: sources.append(c)
    return sources[:8]


def parse_outline(text: str) -> list[OutlineSection]:
    sections = []
    lines = text.split('\n')
    current_heading = None
    current_points = []
    def flush():
        nonlocal current_heading, current_points
        if current_heading:
            sections.append(OutlineSection(heading=current_heading, key_points=list(dict.fromkeys(current_points))[:8]))
    for line in lines:
        raw = line.strip()
        if not raw: continue
        m = re.match(r'^#{2,3}\s+(.+)$', raw) or re.match(r'^\*\*(.+?)\*\*', raw) or re.match(r'^(?:[IVXLCDM]+|[A-Z]|\d+)\.\s+(.+)$', raw)
        if m and len(raw) < 100:
            flush()
            current_heading = m.group(1).strip().rstrip(':')
            current_points = []
            continue
        bp = re.match(r'^[\*\-\u2022]\s+(.+)$', raw) or re.match(r'^\d+[\.\)]\s+(.+)$', raw)
        if bp and current_heading: current_points.append(bp.group(1).strip()[:300])
    flush()
    if not sections: sections.append(OutlineSection(heading='Outline', key_points=[text[:500]]))
    return sections


def parse_edit(text: str) -> tuple:
    coh = min(10, max(0, int(m.group(1)))) if (m := re.search(r'Coherence:\s*(\d+)', text)) else 5
    rel = min(10, max(0, int(m.group(1)))) if (m := re.search(r'Relevance:\s*(\d+)', text)) else 5
    com = min(10, max(0, int(m.group(1)))) if (m := re.search(r'Completeness:\s*(\d+)', text)) else 5
    avg = float(m.group(1)) if (m := re.search(r'Average:\s*([\d.]+)', text)) else (coh + rel + com) / 3
    dec = m.group(1).strip() if (m := re.search(r'Decision:\s*(\w+)', text)) else 'PASS'
    fb = m.group(1).strip() if (m := re.search(r'(?:Issues?|Improvements?|Feedback):\s*(.+)$', text, re.DOTALL)) else None
    if fb:
        fb = re.sub(r'\n\s*Total\s+word\s+count.*$', '', fb, flags=re.IGNORECASE)
        fb = re.sub(r'\n\s*\d+\s*words?.*$', '', fb, flags=re.IGNORECASE)
    return coh, rel, com, avg, dec == 'PASS', fb


# ── ADK Bridge Agent ──
class AdkGeminiBridge(ACSBaseAgent):
    """Wraps a Google ADK agent into our BaseAgent interface.
    
    Each bridge agent holds an ADK Agent + Runner and calls Gemini
    via the ADK framework. The prompt is built from the PipelineContext
    so each stage receives the previous stages' outputs.
    """

    def __init__(self, acs_name: AgentName, adk_agent, adk_runner, session_service):
        super().__init__(name=acs_name)
        self._agent = adk_agent
        self._runner = adk_runner
        self._session_service = session_service

    def _build_prompt(self, inp):
        ctx = inp.context
        T = inp.topic

        if self.name == AgentName.RESEARCH:
            return (
                f'Topic: {T}\n\nYou are the RESEARCH agent. Research this topic thoroughly.\n'
                f'Requirements:\n- Comprehensive summary with key facts, data, dates\n'
                f'- Minimum 500 words\n- Include specific factual statements\n'
                f'- List 5+ academic/professional sources at the end'
            )

        elif self.name == AgentName.PLANNING:
            r = ctx.research
            return (
                f'Topic: {T}\n\nYou are the PLANNING agent.\n\n'
                f'=== RESEARCH ===\n{r.summary if r else ""}\n\n'
                f'=== TASK ===\nCreate 5-8 sections based SOLELY on the research.\n'
                f'Format each:\n### Section Title\n- Key point from research\n'
                f'Output ALL sections. Do not truncate.'
            )

        elif self.name == AgentName.WRITING:
            r, o = ctx.research, ctx.outline
            os_ = ''
            if o:
                for s in o.sections:
                    os_ += f'\n### {s.heading}\n'
                    for kp in s.key_points[:5]: os_ += f'- {kp}\n'
            return (
                f'Topic: {T}\n\nYou are the WRITING agent.\n\n'
                f'=== RESEARCH ===\n{r.summary[:3000] if r else ""}\n\n'
                f'=== OUTLINE (follow EXACTLY) ==={os_}\n\n'
                f'=== TASK ===\nWrite a complete article following the outline EXACTLY.\n'
                f'Expand each section into 2-4 paragraphs. Use facts from research.\n'
                f'1000-2500 words. Complete ALL sections.'
            )

        elif self.name == AgentName.EDITING:
            r, o, d = ctx.research, ctx.outline, ctx.draft
            os_ = ''
            if o:
                for s in o.sections: os_ += f'\n- {s.heading}: {", ".join(s.key_points[:3])}'
            return (
                f'Topic: {T}\n\nYou are the EDITING agent. CRITIQUE — do not praise.\n\n'
                f'=== RESEARCH FACTS ===\n{"; ".join(r.facts[:5]) if r else "None"}\n\n'
                f'=== OUTLINE ==={os_}\n\n'
                f'=== DRAFT ({d.word_count if d else 0} words) ===\n{d.content if d else ""}\n\n'
                f'=== SCORING RUBRIC ===\n'
                f'1. COHERENCE (0-10): Logical gaps? Missing transitions?\n'
                f'2. RELEVANCE (0-10): Every paragraph relate to outline?\n'
                f'3. COMPLETENESS (0-10): ALL outline sections covered?\n\n'
                f'RULES:\n- Never give 10/10 — there are always improvements.\n'
                f'- List 2+ specific flaws even at high scores.\n'
                f'- Be specific: quote sentences, cite missing sections.\n\n'
                f'OUTPUT:\nCoherence: X/10 - justification\nRelevance: X/10 - justification\n'
                f'Completeness: X/10 - justification\nAverage: X.X\n'
                f'Decision: PASS (avg>=7.0) or RETRY (avg<7.0)\n'
                f'Issues: [numbered list of specific problems]'
            )

        elif self.name == AgentName.OPTIMIZATION:
            d, e = ctx.draft, ctx.edit
            ow = d.word_count if d else 500
            target_min = int(ow * 0.95)
            target_max = int(ow * 1.00)
            return (
                f'Topic: {T}\n\nYou are the OPTIMIZATION agent. Polish — DO NOT EXPAND.\n\n'
                f'=== DRAFT ({ow} words) ===\n{d.content if d else ""}\n\n'
                f'=== EDIT FEEDBACK ===\n'
                f'Coherence: {e.scores.coherence}/10, Relevance: {e.scores.relevance}/10, '
                f'Completeness: {e.scores.completeness}/10\n'
                f'Issues: {e.instructions or "None"}\n\n'
                f'=== STRICT RULES ===\n'
                f'1. Output MUST be {target_min}-{target_max} words.\n'
                f'2. DO NOT add new content or remove facts.\n'
                f'3. ONLY improve: word choice, sentence rhythm, transitions, tone.\n'
                f'4. Preserve ALL section headings and structure.\n'
                f'5. No meta-commentary.'
            )

        return f'Topic: {T}'

    async def execute(self, inp):
        sid = f'{inp.job_id}-{self.name.value}'
        _ensure_adk()
        await self._session_service.create_session(
            app_name='acs_pipeline', user_id='acs_user', session_id=sid
        )
        msg = genai_types.Content(
            role='user', parts=[genai_types.Part(text=self._build_prompt(inp))]
        )
        events = []
        async for event in self._runner.run_async(
            user_id='acs_user', session_id=sid, new_message=msg
        ):
            events.append(event)

        result = ''
        for event in reversed(events):
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        result = part.text
                        break
                if result:
                    break

        ctx = inp.context
        if self.name == AgentName.RESEARCH:
            ctx.set('research', ResearchOutput(
                summary=result, facts=extract_facts(result),
                sources=parse_sources(result), raw=result,
            ))
        elif self.name == AgentName.PLANNING:
            ctx.set('outline', OutlineOutput(title=inp.topic, sections=parse_outline(result)))
        elif self.name == AgentName.WRITING:
            ctx.set('draft', DraftOutput(content=result, word_count=len(result.split())))
        elif self.name == AgentName.EDITING:
            rc = ctx.edit.retry_count if ctx.edit else 0
            coh, rel, com, avg, passed, fb = parse_edit(result)
            ctx.overwrite('edit', EditOutput(
                scores=EditScores(coherence=coh, relevance=rel, completeness=com),
                average=avg, passed=passed, retry_count=rc, instructions=fb,
            ))
        elif self.name == AgentName.OPTIMIZATION:
            ctx.set('final', FinalOutput(content=result, word_count=len(result.split()), tone='professional'))

        return AgentOutput(
            job_id=inp.job_id, agent=self.name, result=result,
            metadata=AgentMetadata(config=inp.config, tokens_used=50, latency_ms=500),
            status=AgentStatus.SUCCESS,
        )

# ── Factory ──
_quota_available = True


async def create_adk_pipeline_runner() -> PipelineRunner | None:
    """Create a PipelineRunner with real ADK + Gemini agents.
    
    Returns None if GEMINI_API_KEY is not set or the last known
    Gemini call failed with quota exhaustion.
    """
    global _quota_available

    if not _has_gemini_key():
        logger.info('GEMINI_API_KEY not set — use Phase 1 dummy agents')
        return None

    if not _quota_available:
        logger.info('Gemini recently quota-exhausted — using Phase 1 dummy agents')
        return None

    os.environ['GOOGLE_API_KEY'] = settings.gemini_api_key
    os.environ['GENAI_API_KEY'] = settings.gemini_api_key

    _ensure_adk()
    session_service = InMemorySessionService()
    MODEL = 'gemini-2.5-flash'

    pipeline_agents = {}
    for acs_name, ag_name, instr in [
        (AgentName.RESEARCH,     'research_agent',     'Research topics thoroughly with facts and sources.'),
        (AgentName.PLANNING,     'planning_agent',     'Create detailed outlines from research.'),
        (AgentName.WRITING,      'writing_agent',      'Write full content following the outline exactly.'),
        (AgentName.EDITING,      'editing_agent',      'Critically evaluate drafts — find specific flaws.'),
        (AgentName.OPTIMIZATION, 'optimization_agent', 'Polish tone and style — NEVER expand content.'),
    ]:
        agent = AdkAgent(name=ag_name, model=MODEL, instruction=instr, description=ag_name)
        runner = AdkRunner(agent=agent, app_name='acs_pipeline', session_service=session_service)
        pipeline_agents[acs_name] = AdkGeminiBridge(acs_name, agent, runner, session_service)

    runner = PipelineRunner()
    for name, agent in pipeline_agents.items():
        runner.register_agent(name, agent)

    logger.info('Created ADK + Gemini 2.5 Flash pipeline runner')
    return runner
