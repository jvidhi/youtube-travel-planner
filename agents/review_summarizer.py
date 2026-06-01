import os
import json
import urllib.parse
import urllib.request
import asyncio
import logging
import pydantic
from typing import List, Optional

# Import Google Antigravity SDK
from google.antigravity import Agent, LocalAgentConfig

from config_utils import load_config

logger = logging.getLogger("ReviewSummarizer")


# ==========================================
# 📋 SCHEMAS FOR STRUCTURED OUTPUT
# ==========================================

class PlaceReviewSummary(pydantic.BaseModel):
    place_id: str
    name: str
    average_rating: float
    suitability_analysis: str  # How this place matches user intent (e.g. kid-friendly, couple dining)
    key_highlights: List[str]  # Highlights compiled from actual customer reviews
    reviews_summary: str       # Synthesized, concise summary of user reviews

class ReviewSynthesizerOutput(pydantic.BaseModel):
    summaries: List[PlaceReviewSummary]


# ==========================================
# 🛠️ CUSTOM TOOLS FOR ANTIGRAVITY AGENT
# ==========================================

def google_places_details_reviews(place_id: str) -> str:
    """Queries the Google Places Details API to fetch live user reviews and details of a location.
    
    Args:
        place_id: The standard Google Place ID of the business.
        
    Returns:
        JSON string containing location details, ratings, and raw customer reviews.
    """
    config = load_config()
    api_key = config.get("apiKeys", {}).get("maps")
    if not api_key:
        return json.dumps({"error": "Google Maps API Key is missing in config.json"})

    api_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,reviews&key={api_key}"
    
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "OK" and data.get("result"):
                return json.dumps(data["result"], indent=2)
            return json.dumps({"error": f"Place ID {place_id} not found or has no reviews"})
    except Exception as e:
        return json.dumps({"error": f"Google Places Details API query failed: {str(e)}"})


# ==========================================
# 🧭 REVIEW SUMMARIZER AGENT CLASS
# ==========================================

class ReviewSummarizer:
    def __init__(self):
        self.config_data = load_config()
        self.gemini_key = self.config_data.get("apiKeys", {}).get("gemini", "")
        self.gemini_model = self.config_data.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-2.5-flash")

    async def summarize_reviews(self, places_list: List[dict], intent_query: str) -> ReviewSynthesizerOutput:
        logger.info(f"Review Summarizer engaging for {len(places_list)} locations...")
        
        sys_instructions = (
            "You are an expert Customer Reviews Synthesizer. Your goal is to read raw review inputs "
            "for various travel spots (hotels, restaurants, attractions) and produce structured, in-depth summaries. "
            "You MUST call your 'google_places_details_reviews' tool to fetch the actual live reviews for each place ID. "
            "You then summarize user experiences, highlights, pros and cons, and actively analyze whether the feedback "
            "satisfies the user's custom trip intent (e.g., analyzing if families praise the toddler friendliness of a hotel)."
        )

        agent_config = LocalAgentConfig(
            model=self.gemini_model,
            api_key=self.gemini_key,
            system_instructions=sys_instructions,
            tools=[google_places_details_reviews],
            response_schema=ReviewSynthesizerOutput
        )

        async with Agent(config=agent_config) as agent:
            prompt = (
                f"Please retrieve and synthesize real customer reviews for the following locations:\n"
                f"{json.dumps(places_list, indent=2)}\n\n"
                f"Trip style / User Intent query: \"**{intent_query}**\"\n\n"
                f"For each location in the list:\n"
                f"1. Call 'google_places_details_reviews' with its Place ID.\n"
                f"2. Read the reviews text. Summarize key highlights, and analyze suitability for the user's intent.\n"
                f"3. Construct the structured ReviewSynthesizerOutput object."
            )
            
            response = await agent.chat(prompt)
            structured_data = await response.structured_output()
            if not structured_data:
                raise ValueError("Review Summarizer failed to produce structured output.")
            return ReviewSynthesizerOutput(**structured_data)
