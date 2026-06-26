import time
from packages.shared.base_agent import BaseAgent
from packages.shared.schemas import AgentInput, AgentOutput


class PlanningAgent(BaseAgent):
    async def execute(self, input: AgentInput) -> AgentOutput:
        start_time = time.time()

        try:
            research_context = input.context.get("research", {})
            summary = research_context.get("summary", "")
            facts = research_context.get("facts", [])

            memory_context = await self.retrieve_from_memory(input.topic)

            prompt = f"""
You are a content planning agent.

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

            response = await self.model.generate(prompt)

            latency_ms = int((time.time() - start_time) * 1000)

            return AgentOutput(
                job_id=input.job_id,
                agent="planning",
                result=response,
                metadata={
                    "model": input.config.model,
                    "tokens": getattr(response, "tokens", 0),
                    "latency_ms": latency_ms,
                },
                status="success",
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            return AgentOutput(
                job_id=input.job_id,
                agent="planning",
                result=f"Planning failed: {str(e)}",
                metadata={
                    "model": input.config.model,
                    "tokens": 0,
                    "latency_ms": latency_ms,
                },
                status="failed",
            )
