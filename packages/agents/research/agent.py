"""Research Agent — stub for Member 1.

TODO: Implement web search + content extraction with MCP tools, then
save findings to LightRAG.
"""

import logging
from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, ResearchOutput
from acs_shared.constants import AgentName, AgentStatus

logger = logging.getLogger(__name__)

try:
    from google.adk.tools.mcp_toolset import MCPToolset
    from google.adk.tools import StdioServerParameters
    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False


class ResearchAgent(BaseAgent):
    """Research Agent — searches the web, extracts content, saves to LightRAG.

    **Instructions for Member 1 — implement execute():**

    1. Load the research prompt from ``prompts/research.md``
       - ``prompt = self.load_prompt('research')``
    2. Append the user's topic and any context
    3. (Phase 2) Run Open-WebSearch MCP to search the web
    4. (Phase 2) Run Scrapling MCP to extract content from top results
    5. (Phase 2) Save extracted content to LightRAG via
       ``await self.save_to_memory(text, metadata)``
    6. Call the LLM: ``text, tokens, latency = await self.generate_text(prompt)``
    7. Parse the LLM output into a ``ResearchOutput(summary=..., facts=[...],
       sources=[...], raw=...)``
    8. Save it: ``input.context.set('research', output)``
    9. Return an ``AgentOutput`` with status ``AgentStatus.SUCCESS``

    **Contract:**
    - ``input.context.research`` → ``ResearchOutput`` after execute
    - Always use ``self.generate_text()`` — never call an LLM SDK directly
    - Always return ``AgentOutput`` with all fields filled
    """

    def __init__(self):
        super().__init__(name=AgentName.RESEARCH)

    async def execute(self, input: AgentInput) -> AgentOutput:
        # --- YOUR CODE HERE ---
        # 1. Load prompt
        prompt = self.load_prompt('research')
        prompt += f"\n\nTopic: {input.topic}"

        # 2. Call LLM
        text, tokens, latency = await self.generate_text(prompt)

        # 3. Parse output into ResearchOutput
        output = ResearchOutput(
            summary=text[:1200],
            facts=[],
            sources=[],
            raw=text,
        )
        input.context.set('research', output)

        # 4. Return AgentOutput
        return AgentOutput(
            job_id=input.job_id,
            agent=AgentName.RESEARCH,
            result=output.summary,
            metadata=AgentMetadata(
                config=input.config,
                tokens_used=tokens,
                latency_ms=latency,
            ),
            status=AgentStatus.SUCCESS,
        )


root_agent = ResearchAgent()
