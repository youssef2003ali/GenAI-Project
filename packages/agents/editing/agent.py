import logging

from acs_shared.base_agent import BaseAgent
from acs_shared.schemas import (
    AgentInput,
    AgentOutput,
    AgentMetadata,
    EditOutput,
    EditScores,
)
from acs_shared.constants import AgentName, AgentStatus
from acs_shared.utils import parse_edit_scores

logger = logging.getLogger(__name__)


class EditingAgent(BaseAgent):
    """Reviews draft quality and decides whether it passes."""

    def __init__(self):
        super().__init__(name=AgentName.EDITING)

    async def execute(self, input: AgentInput) -> AgentOutput:
        try:
           
            draft_text = (
                input.context.draft.content
                if input.context.draft
                else ""
            )

            if not draft_text.strip():
                raise ValueError("No draft found in pipeline context.")

          
            prompt = self.load_prompt("editing")

            prompt += f"""

Topic:
{input.topic}

Draft:
{draft_text}

Evaluate the draft using ONLY the following format:

Coherence: <0-10>
Relevance: <0-10>
Completeness: <0-10>
Average: <number>
Decision: PASS or RETRY
Issues:
- Specific improvement 1
- Specific improvement 2
"""

          
            text, tokens, latency = await self.generate_text(prompt)

          
            scores = parse_edit_scores(text)

            average = scores["average"]
            passed = scores["passed"]

            retry_count = (
                input.context.edit.retry_count
                if input.context.edit
                else 0
            )

           
            edit_output = EditOutput(
                scores=EditScores(
                    coherence=scores["coherence"],
                    relevance=scores["relevance"],
                    completeness=scores["completeness"],
                ),
                average=average,
                passed=passed,
                retry_count=retry_count,
                instructions=scores["issues"],
            )

            input.context.set("edit", edit_output)

            
            status = (
                AgentStatus.SUCCESS
                if passed
                else AgentStatus.RETRY
            )

            return AgentOutput(
                job_id=input.job_id,
                agent=AgentName.EDITING,
                result=text,
                metadata=AgentMetadata(
                    config=input.config,
                    tokens_used=tokens,
                    latency_ms=latency,
                    retry_count=retry_count,
                ),
                status=status,
            )

        except Exception as e:
            logger.exception("EditingAgent failed")

            return AgentOutput(
                job_id=input.job_id,
                agent=AgentName.EDITING,
                result=f"Editing failed: {str(e)}",
                metadata=AgentMetadata(
                    config=input.config,
                    tokens_used=0,
                    latency_ms=0,
                    retry_count=(
                        input.context.edit.retry_count
                        if input.context.edit
                        else 0
                    ),
                ),
                status=AgentStatus.FAILED,
            )


root_agent = EditingAgent()
