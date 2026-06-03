import inspect
from google.adk import Agent
from google.adk import tools
print("Agent fields:", Agent.model_fields.keys())
print("Tools module dir:", dir(tools))
if hasattr(tools, 'Tool'):
    print("Tool fields:", tools.Tool.model_fields.keys())
