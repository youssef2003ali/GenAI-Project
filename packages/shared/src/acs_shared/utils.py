"""Utility functions for fact extraction, source parsing, and editing score parsing."""

import re


def extract_facts(text: str, max_facts: int = 8) -> list[str]:
    """Extract factual sentences from research text, filtering out headings and non-facts.

    Skips markdown headings (###, ##, **bold**), list markers, and empty lines.
    Only keeps sentences containing factual signals (is, was, discovered, measured, etc.).
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    facts = []

    for s in sentences:
        s = s.strip()
        # Skip: empty, too short, headings, list items, source lines
        if not s or len(s) < 30:
            continue
        if re.match(r'^#', s):
            continue
        if re.match(r'^[*\-]\s', s):
            continue
        if re.match(r'^\d+[\.\)]\s', s):
            continue
        if s.startswith('http') or s.startswith('---'):
            continue
        # Must contain factual signal keywords
        has_signal = any(kw in s.lower() for kw in [
            ' is ', ' was ', ' are ', ' were ', ' has ', ' have ', ' had ',
            ' discovered', ' developed ', ' created ', ' found ',
            ' shown ', ' demonstrated ', ' consists ', ' contains ',
            ' measured ', ' estimated ', ' according to ',
            ' study ', ' research ', ' data ', ' percent ', '%',
            ' million', ' billion', ' thousand',
            ' km ', ' kg ', ' years ', ' century',
            '19', '20', '202', '203', '204',
        ])
        if has_signal:
            clean = s.lstrip('*#- ').strip()
            if clean not in facts:
                facts.append(clean[:300])
                if len(facts) >= max_facts:
                    break

    return facts if facts else [text[:200]]


def parse_sources(text: str) -> list[str]:
    """Extract source citations from research text.

    Looks for numbered source lists, markdown links, and citation patterns.
    Returns formatted source strings.
    """
    sources = []
    lines = text.split('\n')
    in_source_block = False

    for line in lines:
        s = line.strip()
        if not s:
            continue

        # Detect source section headers
        if re.match(r'^#{1,3}\s*(Sources?|References?|Bibliography|Works?\s*Cited)', s, re.IGNORECASE):
            in_source_block = True
            continue
        if in_source_block and re.match(r'^#{1,3}\s', s):
            in_source_block = False
            continue

        if in_source_block:
            # Collect numbered sources, markdown links, and citation lines
            if re.match(r'^\d+[\.\)]\s', s) or re.match(r'^[*\-]\s', s) or re.match(r'^\[', s):
                clean = re.sub(r'^\d+[\.\)]\s*', '', s)
                clean = re.sub(r'^[*\-]\s*', '', clean)
                if clean and len(clean) > 20 and clean not in sources:
                    sources.append(clean[:300])
            elif re.match(r'^https?://', s):
                if s not in sources:
                    sources.append(s[:200])

    # Fallback: find any citation-like patterns outside source block
    if not sources:
        # Author (Year) pattern
        citations = re.findall(r'\([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+))?\s*,\s*\d{4}\)', text)
        for c in citations:
            if c not in sources:
                sources.append(c)
        # Markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
        for title, url in links:
            if len(title) > 10 and f'{title} - {url}' not in sources:
                sources.append(f'{title} - {url}')
                if len(sources) >= 5:
                    break

    return sources[:8]


def parse_edit_scores(text: str) -> dict:
    """Extract edit scores and issues from LLM editing response.

    Returns dict with: coherence, relevance, completeness, average, passed, issues
    """
    result = {
        'coherence': 5,
        'relevance': 5,
        'completeness': 5,
        'average': 0.0,
        'passed': True,
        'issues': None,
    }

    m = re.search(r'Coherence:\s*(\d+)', text)
    if m:
        result['coherence'] = min(10, max(0, int(m.group(1))))

    m = re.search(r'Relevance:\s*(\d+)', text)
    if m:
        result['relevance'] = min(10, max(0, int(m.group(1))))

    m = re.search(r'Completeness:\s*(\d+)', text)
    if m:
        result['completeness'] = min(10, max(0, int(m.group(1))))

    m = re.search(r'Average:\s*([\d.]+)', text)
    if m:
        result['average'] = float(m.group(1))
    else:
        result['average'] = (
            result['coherence'] + result['relevance'] + result['completeness']
        ) / 3

    m = re.search(r'Decision:\s*(\w+)', text)
    if m:
        result['passed'] = m.group(1).strip().upper() == 'PASS'

    # Capture issues/feedback section - everything after "Issues:" or "Feedback:" or "Improvements:"
    # until end or next section heading
    for label in ['Issues:', 'Feedback:', 'Improvements:', 'Issues Found:']:
        pattern = re.escape(label) + r'\s*(.+?)(?:\n\n(?!\d+[\.\)])|\Z)'
        m = re.search(pattern, text, re.DOTALL)
        if m:
            issues = m.group(1).strip()
            # Truncate if it includes the word count footer
            issues = re.sub(r'\n\s*Total\s+word\s+count.*$', '', issues, flags=re.IGNORECASE)
            issues = re.sub(r'\n\s*\d+\s*words?.*$', '', issues, flags=re.IGNORECASE)
            result['issues'] = issues.strip()
            break

    return result
