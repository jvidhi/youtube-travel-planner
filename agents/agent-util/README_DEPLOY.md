# Deploying to Gemini Enterprise Agent Platform

This directory contains a multi-agent travel planning framework ready for deployment to the Gemini Enterprise Agent Platform (Vertex AI Reasoning Engine).

## Prerequisites

1.  **Google Cloud Project**: An active GCP project with the Vertex AI API enabled.
2.  **GCS Bucket**: A Cloud Storage bucket for staging deployment artifacts (e.g., `gs://my-bucket-name`).
3.  **Authentication**: Ensure you are authenticated with Google Cloud:
    ```bash
    gcloud auth application-default login
    ```
4.  **Configuration**: The agents require API keys for Gemini, Google Maps, and YouTube. You can provide these via environment variables or a `config.json` file.

## Deployment Steps

Run the `deploy.py` script:

```bash
python deploy.py --project YOUR_PROJECT_ID --bucket gs://YOUR_STAGING_BUCKET
```

Optional arguments:
- `--location`: The GCP region (default: `us-central1`).

## How it Works

1.  **Orchestrator**: The `orchestrator.py` script defines the `TravelPlannerOrchestrator` class, which serves as the entry point.
2.  **Multi-Agent Coordination**: The orchestrator coordinates three specialized agents:
    - `YouTubeSummarizer`: Extracts travel context from video URLs.
    - `ItineraryPlanner`: Creates a custom itinerary using Google Places data.
    - `ReviewSummarizer`: Synthesizes user reviews for selected places.
3.  **Reasoning Engine**: The `deploy.py` script uses the Vertex AI SDK to package these agents and deploy them as a managed "Reasoning Engine".

## Configuration in the Cloud

When running in the cloud, you should set the following environment variables in the Vertex AI console or via the `ReasoningEngine` instance configuration:

- `GEMINI_API_KEY`
- `MAPS_API_KEY`
- `YOUTUBE_API_KEY`

Alternatively, you can provide a JSON string in `AGENT_CONFIG_JSON`.

## Testing the Deployed Agent

Once deployed, the script will provide a resource name. You can query it using the Vertex AI Python SDK:

```python
from google.cloud import aiplatform

# Replace with your engine's resource name
RESOURCE_NAME = "projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/123456789"

engine = aiplatform.ReasoningEngine(RESOURCE_NAME)
response = engine.query(
    video_url="https://www.youtube.com/watch?v=f4wBcKc2j8s",
    intent_query="plan me a luxury romantic getaway"
)

print(response["report_md"])
```
