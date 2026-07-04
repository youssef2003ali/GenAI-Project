"""Unit tests for the Research Agent.

These tests mock `web_search`, `scrape_content`, and `generate_text` so
they run fast, offline, and deterministically — without spawning any
real MCP subprocesses (Node/npx, Scrapling) or hitting the network.
Real MCP integration should be verified manually or via a dedicated
integration test with generous timeouts, not in the unit suite.
"""

import pytest
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.schemas import AgentOutput


def mock_web_search(results=None):
    results = (
        results
        if results is not None
        else [
            {
                'title': 'Result 1: Artificial Intelligence',
                'url': 'https://example.com/result-1',
                'description': 'AI is transforming industries worldwide in 2024.',
            },
            {
                'title': 'Result 2: Artificial Intelligence',
                'url': 'https://example.com/result-2',
                'description': 'Machine learning models have grown significantly.',
            },
        ]
    )

    async def _search(query, num_results=5):
        return results[:num_results]

    return _search


def mock_scrape_content(content_map=None):
    async def _scrape(url):
        if content_map and url in content_map:
            return content_map[url]
        return (
            f'Extracted content from {url}: AI adoption has increased by '
            f'40 percent since 2022, according to industry research. '
            f'Companies are investing heavily in machine learning infrastructure.'
        )

    return _scrape


def mock_generate_text(text, tokens=42, latency=100):
    async def _gen(prompt):
        return text, tokens, latency

    return _gen


@pytest.fixture
def agent(monkeypatch):
    from research.agent import root_agent

    monkeypatch.setattr(root_agent, 'load_prompt', lambda name: 'PROMPT_HEADER\n')
    monkeypatch.setattr('research.agent.web_search', mock_web_search())
    monkeypatch.setattr('research.agent.scrape_content', mock_scrape_content())
    monkeypatch.setattr(
        root_agent,
        'generate_text',
        mock_generate_text(
            'Artificial intelligence continues to reshape industries in '
            '2024, with significant growth in enterprise adoption and '
            'infrastructure investment across multiple sectors.'
        ),
    )
    return root_agent


class TestResearchAgent:
    """Tests for Research Agent."""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(self, agent, agent_input):
        """Research agent should return valid AgentOutput."""
        output = await agent.execute(agent_input)
        assert isinstance(output, AgentOutput)
        assert output.agent == AgentName.RESEARCH
        assert output.status == AgentStatus.SUCCESS
        assert output.job_id == 'test-job-001'

    @pytest.mark.asyncio
    async def test_populates_research_context(self, agent, agent_input):
        """Research agent should set context.research."""
        ctx = agent_input.context
        await agent.execute(agent_input)
        assert ctx.research is not None
        assert len(ctx.research.facts) > 0
        assert len(ctx.research.sources) > 0

    @pytest.mark.asyncio
    async def test_contains_metadata(self, agent, agent_input):
        """Output should have filled metadata."""
        output = await agent.execute(agent_input)
        assert output.metadata.tokens_used >= 0
        assert output.metadata.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_sources_come_from_search_results(self, agent, agent_input):
        """Sources should be the real URLs returned by web_search."""
        ctx = agent_input.context
        await agent.execute(agent_input)
        assert 'https://example.com/result-1' in ctx.research.sources

    @pytest.mark.asyncio
    async def test_handles_empty_search_results(self, monkeypatch, agent_input):
        """Research should still succeed gracefully with no search results."""
        from research.agent import root_agent

        monkeypatch.setattr(root_agent, 'load_prompt', lambda name: 'PROMPT_HEADER\n')
        monkeypatch.setattr('research.agent.web_search', mock_web_search(results=[]))
        monkeypatch.setattr('research.agent.scrape_content', mock_scrape_content())
        monkeypatch.setattr(
            root_agent,
            'generate_text',
            mock_generate_text('A general summary based on existing knowledge of the topic.'),
        )

        output = await root_agent.execute(agent_input)
        assert output.status == AgentStatus.SUCCESS
        assert agent_input.context.research is not None
