import inspect
from google.adk.tools import FunctionTool
print(inspect.signature(FunctionTool.__init__))
