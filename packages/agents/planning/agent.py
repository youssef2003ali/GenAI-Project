import json
import time
from acs_shared.base_agent import BaseAgent
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.schemas import AgentInput, AgentOutput, AgentMetadata, OutlineOutput, OutlineSection


class PlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(name=AgentName.PLANNING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        start_time = time.time()

        try:
            research = input.context.research
            summary = research.summary if research else ''
            facts = research.facts if research else []

            memory_context = await self.retrieve_from_memory(input.topic)

            prompt = f"""You are a content planning agent.

Topic:
{input.topic}

Research Summary:
{summary}

Facts:
{facts}

Additional Context:
{memory_context}

Generate a content outline in valid JSON only.

Format:

{{
  "title": "content title",
  "sections": [
    {{
      "heading": "Section title",
      "key_points": ["point 1", "point 2"]
    }}
  ]
}}

Rules:
- Create between 3 and 7 sections.
- Each section must contain 2-5 key points.
- Output valid JSON only.
"""

            text, tokens, latency_ms = await self.generate_text(prompt)

            raw = text.strip()
            if raw.startswith('```json'):
                raw = raw.removeprefix('```json').removesuffix('```').strip()
            elif raw.startswith('```'):
                raw = raw.removeprefix('```').removesuffix('```').strip()
            outline_data = json.loads(raw)
            sections = [OutlineSection(**s) for s in outline_data['sections']]
            outline = OutlineOutput(title=outline_data['title'], sections=sections)
            input.context.set('outline', outline)

            return AgentOutput(
                job_id=input.job_id,
                agent=AgentName.PLANNING,
                result=json.dumps(outline_data, indent=2),
                metadata=AgentMetadata(
                    config=input.config,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                ),
                status=AgentStatus.SUCCESS,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            return AgentOutput(
                job_id=input.job_id,
                agent=AgentName.PLANNING,
                result=f'Planning failed: {str(e)}',
                metadata=AgentMetadata(
                    config=input.config,
                    tokens_used=0,
                    latency_ms=latency_ms,
                ),
                status=AgentStatus.FAILED,
            )


root_agent = PlanningAgent()
