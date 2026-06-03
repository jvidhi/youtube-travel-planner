import os
import argparse
from google.cloud import aiplatform
import vertexai
from vertexai.preview import reasoning_engines
from orchestrator import TravelPlannerOrchestrator

def deploy(project_id: str, location: str, staging_bucket: str):
    """
    Deploys the TravelPlannerOrchestrator as a multi-agent framework on Gemini Enterprise Agent Platform.
    (Vertex AI Reasoning Engine)
    """
    print(f"Initializing Vertex AI with project={project_id}, location={location}, staging_bucket={staging_bucket}")
    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    print("Creating TravelPlannerOrchestrator Reasoning Engine...")
    
    # Requirements for the Reasoning Engine
    # These must match the environment needed to run the agents
    requirements = [
        "google-adk>=0.1.0",
        "pydantic>=2.0.0",
        "google-cloud-aiplatform[reasoningengine]>=1.50.0",
        "cloudpickle>=3.0.0",
        "nest-asyncio>=1.6.0",
    ]

    # Deploy the Reasoning Engine
    # extra_packages=["."] tells Vertex AI to include all files in the current directory (the agents)
    engine = reasoning_engines.ReasoningEngine.create(
        TravelPlannerOrchestrator(),
        requirements=requirements,
        display_name="Travel Planner Multi-Agent Framework",
        description="A multi-agent framework that uses YouTube, Google Places, and Review synthesis to plan trips.",
        extra_packages=["."],
    )

    print("\n" + "="*50)
    print("🎉 DEPLOYMENT SUCCESSFUL!")
    print(f"Resource Name: {engine.resource_name}")
    print(f"Engine ID: {engine.resource_name.split('/')[-1]}")
    print("="*50 + "\n")
    
    print("To test your deployed agent, you can use the following Python code:")
    print(f"""
    from vertexai.preview import reasoning_engines
    remote_engine = reasoning_engines.ReasoningEngine("{engine.resource_name}")
    response = remote_engine.query(
        video_url="https://www.youtube.com/watch?v=f4wBcKc2j8s",
        intent_query="plan me a family friendly trip"
    )
    print(response["report_md"])
    """)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy Travel Planner Multi-Agent Framework to Gemini Enterprise Agent Platform")
    parser.add_argument("--project", type=str, help="Google Cloud Project ID", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", type=str, help="Google Cloud Location", default=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"))
    parser.add_argument("--bucket", type=str, help="Cloud Storage Staging Bucket (gs://bucket-name)", default=os.getenv("STAGING_BUCKET"))

    args = parser.parse_args()

    if not args.project:
        print("Error: Project ID is required. Use --project or set GOOGLE_CLOUD_PROJECT environment variable.")
        exit(1)
    if not args.bucket:
        print("Error: Staging bucket is required. Use --bucket or set STAGING_BUCKET environment variable.")
        exit(1)

    deploy(args.project, args.location, args.bucket)
