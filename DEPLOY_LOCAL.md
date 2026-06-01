# Local Deployment Guide (Aura Voyage)

This guide provides instructions on how to run the Aura Voyage application locally on your machine.

## Architecture: Do we need `server.py`?

**Yes, `server.py` is required for the full experience.**

While the `README.md` suggests you can run a static `http.server` to view the frontend in "Sandbox Demo Mode", `server.py` is the actual asynchronous Python backend that orchestrates the AI agents. 

Here is what `server.py` does:
1. **Serves the Frontend UI:** It mounts and serves `index.html`, `app.js`, and `styles.css`.
2. **Hosts the Agentic API:** It exposes the `/api/plan` endpoint. When you input a YouTube URL in the UI, `app.js` sends a POST request to this endpoint. `server.py` then triggers the `TravelPlannerOrchestrator` (which uses Gemini, YouTube APIs, and custom Python agents) to generate the live trip plan.

## How to run the code locally (Your Starting Point)

To run the full application with the backend AI agents interacting with your frontend, `server.py` is your starting point.

### Step 1: Set up the Python Environment

Make sure you have a virtual environment set up and activated:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Requirements

Install the required agent dependencies. Note that since `server.py` uses `starlette` and `uvicorn` to host the web API, you'll need to install them as well:
```bash
pip install -r agents/agent-util/requirements.txt
pip install starlette uvicorn
```

### Step 3: Configure API Keys

Ensure your `config.json` is populated with the necessary API keys (YouTube, Gemini, Google Maps) to allow the agents to fetch live data. If no keys are provided, the application might only function in sandbox mode or the agents will fail to execute.

### Step 4: Start the Server

Run `server.py` using Python:
```bash
python server.py
```

### Step 5: Access the Application

Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**
