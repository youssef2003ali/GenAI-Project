from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handler import DefaultRequestHandler
from .agent import root_agent
import uvicorn

handler = DefaultRequestHandler(agent_executor=root_agent)
app = A2AStarletteApplication(agent_card=root_agent.card, handler=handler)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8102)
