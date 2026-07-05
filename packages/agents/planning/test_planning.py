import pytest
from unittest.mock import AsyncMock

from packages.agents.planning.agent import PlanningAgent


@pytest.mark.asyncio
async def test_planning_agent_success():
    agent = PlanningAgent()

    agent.model = AsyncMock()
    agent.retrieve_from_memory = AsyncMock(return_value="Extra context")

    agent.model.generate = AsyncMock(
        return_value='{"title":"AI","sections":[{"heading":"Intro","key_points":["Definition","History"]}]}'
    )

    class Config:
        model = "nousresearch/hermes-3-405b-instruct:free"

    class InputData:
        job_id = "123"
        topic = "Artificial Intelligence"
        context = {
            "research": {
                "summary": "AI summary",
                "facts": ["Fact 1", "Fact 2"]
            }
        }
        config = Config()

    output = await agent.execute(InputData())

    assert output.status == "success"
