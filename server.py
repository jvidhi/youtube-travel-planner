import os
import sys
import json
import asyncio
import logging
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))

from agents.orchestrator import TravelPlannerOrchestrator

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TravelServer")

orchestrator = TravelPlannerOrchestrator()
base_dir = os.path.dirname(os.path.abspath(__file__))


async def serve_index(request):
    """Serves index.html securely."""
    index_path = os.path.join(base_dir, "index.html")
    return FileResponse(index_path)


async def api_plan(request):
    """Endpoint to execute the multi-agent coordinated travel planner."""
    try:
        body = await request.json()
        video_url = body.get("url")
        intent_query = body.get("intent", "plan me a family friendly trip")
        
        if not video_url:
            return JSONResponse({"error": "Missing YouTube video URL"}, status_code=400)
            
        logger.info(f"Received API planning request: {video_url} | Intent: {intent_query}")
        
        # Run coordinated pipeline
        result = await orchestrator.coordinate_plan(video_url, intent_query)
        
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Coordinated planning execution failed: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Failed to parse/execute planning sequence: {str(e)}"}, status_code=500)


# Build Starlette Application
app = Starlette(
    routes=[
        Route("/", serve_index, methods=["GET"]),
        Route("/api/plan", api_plan, methods=["POST"]),
        # Mount static files directory to serve CSS, JS, and configs
        Mount("/", app=StaticFiles(directory=base_dir), name="static")
    ],
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    ]
)


if __name__ == "__main__":
    # Run server on port 8000
    logger.info("Starting unified Aura Voyage dynamic travel server on http://127.0.0.1:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
