# Aura Voyage 🧭 — YouTube-Driven Trip Planner

A premium, high-fidelity, single-page web application that compiles fully detailed, interactive travel itineraries from a travel YouTube video URL. Built using vanilla web technologies (HTML5, CSS3, and ES6 JavaScript) with an agentic AI design system, interactive visual maps, and customizable workspace options.

---

## 🌟 Features & Architectural Flow

The app emulates an agentic workflow consisting of two distinct AI stages:

### 1. Stage 1: YouTube Summarizer Agent
* **YouTube oEmbed Retrieval**: Automatically parses the video ID from standard YouTube links and queries the oEmbed service to render video previews and author cards without any CORS issues.
* **YouTube Summarizer (Stage 1)**: Grounded parsing compiles all crucial video details into visual tabs:
  * **Places**: Landmarks and points of interest categorized with metadata tags.
  * **Hotels**: Lodging opportunities matching budget parameters.
  * **Tips**: Connectivity advice (SIM cards, Pocket Wi-Fi) and transit solutions.
  * **YT Notes**: Raw grounded chronological summaries from the video description/transcript.

### 2. Stage 2: Gemini Itinerary Planner Agent
* **Grounded Map Correlation**: Correlates places on active maps (Google Maps or custom Vector Canvas).
* **Workspace Customization**:
  * **Pace Slider**: Dynamic switches (Relaxed ☕, Balanced 🚶, Fast-Paced 🏃) change activities volume in real time.
  * **Budget Selector**: Tailors accommodations and selections (Budget 🎒, Moderate 💳, Luxury 💎) instantly.
  * **Focus Vibes Toggles**: Refines the active timeline to reflect focus styles (Sightseeing, Foodie, Adventure).
* **Dynamic Alternative Swaps**: Injects alternative options into each itinerary day, enabling users to click to swap destinations or dining stops interactively!
* **Interactive Map Integration**: Plot all markers dynamically. Supports live Google Maps API or draws a premium vector canvas showing routes, highways, and glowing markers if no API key is configured.

---

## 🔒 Security & Compliance

This application was built strictly adhering to the **Mandatory Secure Web Skills**:
* **XSS Prevention**:
  * **Strictly zero `innerHTML` assignments**. All DOM elements are created programmatically using `document.createElement()` and safely appended.
  * **Secure Text Renders**: Dynamic parameters are set using `textContent` or `innerText` exclusively.
  * **HTML Sanitization**: Integrates `DOMPurify` via CDN with Subresource Integrity (SRI) verification for all output parameters.
* **Data Seeding**: Stores API Keys securely on `localStorage` entirely client-side.

---

## 🚀 Getting Started

### 1. Project & API Configuration (config.json)
All external context is completely isolated out of the codebase. You can configure the application using the central **`config.json`** configuration file:
* **`gcp.projectId`**: Google Cloud project ID context.
* **`models.gemini.activeModelId`**: The active model to load (e.g., `gemini-2.5-flash`, `gemini-flash-latest`).
* **`maps.apiVersion`**: Active release channel for Google Maps script (e.g., `weekly`, `quarterly`).
* **`youtube.apiVersion`**: YouTube Data API reference.

### 2. Live API Keys Setup
Click the **Gear Button** in the header to open the integrations modal:
* **Google Gemini API Key**: To generate dynamic live plans from any arbitrary travel video.
* **YouTube Data API Key**: To extract video snippet description metadata.
* **Google Maps API Key**: For Google Maps rendering with custom themed styles and route lines.

*Note: If no API keys are entered, the application operates in **Sandbox Demo Mode**, allowing you to instantly explore three pre-seeded presets (Tokyo, Amalfi Coast, Iceland) with high-fidelity interactive coordinates and details.*

### 2. Local Execution
Run a local HTTP server from this directory to launch the application in your browser.

#### Using Python:
```bash
python3 -m http.server 8000
```

#### Using Node.js / Live Server:
```bash
npx serve .
```

Open `http://localhost:8000` or `http://localhost:3000` in your browser.
