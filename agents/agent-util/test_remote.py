from vertexai.preview import reasoning_engines
import vertexai
import traceback

vertexai.init(project="vertex-ai-382806", location="us-central1")

engine_id = "projects/433578906282/locations/us-central1/reasoningEngines/2283107857530355712"
print(f"Connecting to remote engine: {engine_id}")

try:
    remote_engine = reasoning_engines.ReasoningEngine(engine_id)
    print("Engine connected. Sending query...")
    response = remote_engine.query(
        video_url="https://www.youtube.com/watch?v=f4wBcKc2j8s",
        intent_query="plan me a family friendly trip"
    )
    print("Response received!")
    print(response.get("report_md", "No report_md found in response."))
except Exception as e:
    traceback.print_exc()
