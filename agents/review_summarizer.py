import json
import os
import uuid
import urllib.parse
import urllib.request
import asyncio
import logging
import pydantic
from typing import List, Optional

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai.types import Content, Part

from config_utils import load_config
from agent_hooks import before_tool_callback, after_tool_callback, on_tool_error_callback

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
    logger.info(f"🔧 Tool execution: google_places_details_reviews(place_id='{place_id}')")
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
    def __init__(self, model_id: str = "gemini-3.5-flash"):
        self.gemini_model = model_id
        
        sys_instructions = (
            "You are an expert Customer Reviews Synthesizer. Your goal is to read raw review inputs "
            "for various travel spots (hotels, restaurants, attractions) and produce structured, in-depth summaries. "
            "You MUST call your 'google_places_details_reviews' tool to fetch the actual live reviews for each place ID. "
            "You then summarize user experiences, highlights, pros and cons, and actively analyze whether the feedback "
            "satisfies the user's custom trip intent (e.g., analyzing if families praise the toddler friendliness of a hotel)."
        )

        review_details_tool = FunctionTool(google_places_details_reviews)

        self.agent = Agent(
            name="review_summarizer",
            model=self.gemini_model,
            instruction=sys_instructions,
            tools=[review_details_tool],
            output_schema=ReviewSynthesizerOutput,
            before_tool_callback=before_tool_callback,
            after_tool_callback=after_tool_callback,
            on_tool_error_callback=on_tool_error_callback
        )
        self.runner = InMemoryRunner(agent=self.agent)

    async def summarize_reviews(self, places_list: List[dict], intent_query: str) -> ReviewSynthesizerOutput:
        logger.info(f"Review Summarizer engaging for {len(places_list)} locations...")
        
        prompt = (
            f"Please retrieve and synthesize real customer reviews for the following locations:\n"
            f"{json.dumps(places_list, indent=2)}\n\n"
            f"Trip style / User Intent query: \"**{intent_query}**\"\n\n"
            f"For each location in the list:\n"
            f"1. Call 'google_places_details_reviews' with its Place ID.\n"
            f"2. Read the reviews text. Summarize key highlights, and analyze suitability for the user's intent.\n"
            f"3. Construct the structured ReviewSynthesizerOutput object."
        )

        logger.info(f"🧠 Prompting Gemini Model ({self.gemini_model}) to analyze and synthesize reviews...")

        try:
            # ADK requires explicit session creation
            session_id = f"sess_{uuid.uuid4()}"
            await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="default_user",
                session_id=session_id
            )
            
            final_output = None
            msg = Content(role="user", parts=[Part.from_text(text=prompt)])
            async for event in self.runner.run_async(user_id="default_user", session_id=session_id, new_message=msg):
                logger.info(f"⚙️  Agent Event: Processing step in review_summarizer...")
                if hasattr(event, "output") and event.output:
                    final_output = event.output
                elif hasattr(event, "content") and event.content and event.content.parts:
                    text_val = event.content.parts[0].text
                    if text_val:
                        
                        try:
                            final_output = json.loads(text_val)
                        except:
                            final_output = text_val
            
            structured_data = final_output
            
            if not structured_data:
                raise ValueError("Review Summarizer failed to produce structured output.")
            
            if isinstance(structured_data, dict):
                return ReviewSynthesizerOutput(**structured_data)
            return structured_data
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise ValueError(f"Review Summarizer failed: {e}")
