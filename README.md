# Aura Voyage 🧭 — YouTube-Driven Trip Planner

A premium, high-fidelity, single-page web application that compiles fully detailed, interactive travel itineraries from a travel YouTube video URL. Built using vanilla web technologies (HTML5, CSS3, and ES6 JavaScript) on the frontend, and a multi-agent Python backend powered by the **Google Agent Development Kit (ADK)**.

---

## 🌟 Features & Architectural Flow

The application uses a coordinated multi-agent orchestration pipeline to transform video content into a actionable travel plan:

### 1. Stage 1: YouTube Summarizer Agent (Google ADK)
* **Concurrent Context Extraction**: Optimized performance using Python's `asyncio` to pre-fetch YouTube transcripts and metadata simultaneously, significantly reducing LLM latency.
* **Intelligent Summarization**: Extracts landmarks, hotels, and transit tips into a structured format:
  * **Places**: Landmarks and points of interest categorized with metadata tags.
  * **Hotels**: Lodging opportunities matched to the video grounding.
  * **Tips**: Connectivity advice and transit solutions.

### 2. Stage 2: Gemini Itinerary Planner Agent
* **Grounded Planning**: Builds a logical day-by-day itinerary based on the summarized video context and user intent.
* **Dynamic Alternative Swaps**: Injects alternative options into each itinerary day, enabling users to explore variations.

### 3. Stage 3: Nearby Attractions & AI Ranking
* **Intent-Aware Curation**: Automatically triggers a Google Places discovery loop for recommended hotels.
* **AI Concierge**: A specialized Gemini agent analyzes nearby spots and ranks the top 3 based on your specific trip intent (e.g., "toddler friendly", "nightlife", or "quiet retreat").

### 4. Stage 4: Interactive Route Mapping
* **Active Route Plotting**: A custom vector mapping engine that parses GPS coordinates from the plan to draw interactive markers and animated path lines ("Active Route") on a themed canvas.

---

## 🔒 Security & Compliance

* **XSS Prevention**: Strictly zero `innerHTML` assignments. All DOM elements are created programmatically with `DOMPurify` sanitization.
* **Credential Protection**: Protects API keys using local `config.json` isolation and frontend `localStorage`.

---

## 🚀 Getting Started

### 1. Configuration (`config.json`)
Rename `config<to_be_edited>.json` to `config.json` and provide your API keys:
* **`apiKeys.gemini`**: For LLM orchestration (Google ADK).
* **`apiKeys.youtube`**: To extract video metadata.
* **`apiKeys.maps`**: For Places discovery and GPS grounding.
* **`models.gemini.activeModelId`**: Set your preferred Gemini model (e.g., `gemini-2.0-flash`).

### 2. Local Deployment
To run the full agentic experience (Frontend + Backend), follow the detailed steps in:
👉 **[DEPLOY_LOCAL.md](./DEPLOY_LOCAL.md)**

### 3. Cloud Deployment (Vertex AI)
This codebase is fully compatible with the **Vertex AI Agent Platform (Reasoning Engine)**. You can deploy your agents as a managed enterprise endpoint using the provided deployment utility:
```bash
python agents/agent-util/deploy.py --project YOUR_PROJECT_ID --bucket gs://YOUR_STAGING_BUCKET
```

---

## 🛠️ Tech Stack
* **Frontend**: Vanilla JS (ES6+), HTML5, CSS3, FontAwesome.
* **Backend**: Python 3.10+, Starlette, Uvicorn.
* **Agent Framework**: Google Agent Development Kit (ADK).
* **AI Models**: Gemini 1.5/2.0 series via Vertex AI / Google AI Studio.
