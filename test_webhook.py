from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
import asyncio

def my_tool(x: int) -> int:
    return x * 2

def after_hook(name, result):
    print("HOOK TRIGGERED. Result:", result)
    return "OVERRIDDEN RESULT"

agent = Agent(
    name="test",
    model="gemini-3.5-flash",
    instruction="Use the tool.",
    tools=[FunctionTool(my_tool)],
    after_tool_callback=after_hook
)

async def main():
    runner = InMemoryRunner(agent=agent)
    await runner.session_service.create_session("app", "user", "sess1")
    msg = Content(role="user", parts=[Part.from_text("Calculate 5 times 2 using your tool.")])
    async for event in runner.run_async("user", "sess1", msg):
        if event.type == "TOOL_RESULT":
             print("TOOL_RESULT Event:", getattr(event, 'output', None) or event)

asyncio.run(main())
