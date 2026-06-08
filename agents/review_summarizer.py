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

from agent_hooks import before_tool_callback, after_tool_callback, on_tool_error_callback

logger = logging.getLogger("ReviewSummarizer")

class PlaceReviewSummary(pydantic.BaseModel):
    place_id: str
    name: str
    average_rating: float
    suitability_analysis: str
    key_highlights: List[str]
    reviews_summary: str

class ReviewSynthesizerOutput(pydantic.BaseModel):
    summaries: List[PlaceReviewSummary]

class ReviewSummarizer:
    def __init__(self, maps_key: str, model_id: str = "gemini-3.5-flash"):
        self.maps_key = maps_key
        self.gemini_model = model_id
        
        sys_instructions = (
            "You are an expert Customer Reviews Synthesizer. Your goal is to read raw review inputs "
            "for various travel spots (hotels, restaurants, attractions) and produce structured, in-depth summaries. "
            "You MUST call your 'google_places_details_reviews' tool to fetch the actual live reviews for each place ID. "
            "You then summarize user experiences, highlights, pros and cons, and actively analyze whether the feedback "
            "satisfies the user's custom trip intent."
        )

        review_details_tool = FunctionTool(self.google_places_details_reviews)

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

    def google_places_details_reviews(self, place_id: str) -> str:
        """Queries the Google Places Details API to fetch live user reviews and details of a location."""
        logger.info(f"🔧 Tool execution: google_places_details_reviews(place_id='{place_id}')")
        if not self.maps_key:
            return json.dumps({"error": "Google Maps API Key is missing"})

        api_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,reviews&key={self.maps_key}"
        
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "OK" and data.get("result"):
                    return json.dumps(data["result"], indent=2)
                return json.dumps({"error": f"Place ID {place_id} not found or has no reviews"})
        except Exception as e:
            return json.dumps({"error": f"Google Places Details API query failed: {str(e)}"})

    async def summarize_reviews(self, places_list: List[dict], intent_query: str) -> ReviewSynthesizerOutput:
        logger.info(f"Review Summarizer engaging for {len(places_list)} locations...")
        
        prompt = (
            f"Please retrieve and synthesize real customer reviews for the following locations:\n"
            f"{json.dumps(places_list, indent=2)}\n\n"
            f"Trip style / User Intent query: \"**{intent_query}**\"\n\n"
            f"For each location:\n"
            f"1. Call 'google_places_details_reviews' with its Place ID.\n"
            f"2. Read the reviews text. Summarize key highlights, and analyze suitability.\n"
            f"3. Construct the structured output."
        )

        logger.info(f"🧠 Prompting Gemini Model ({self.gemini_model}) to analyze and synthesize reviews...")

        session_id = f"sess_{uuid.uuid4()}"
        try:
            await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="default_user",
                session_id=session_id
            )
            
            final_output = None
            full_text = ""
            msg = Content(role="user", parts=[Part.from_text(text=prompt)])
            async for event in self.runner.run_async(user_id="default_user", session_id=session_id, new_message=msg):
                if hasattr(event, "tool_calls") and event.tool_calls:
                    logger.info(f"🔧 Agent is calling tool.")
                elif hasattr(event, "tool_results") and event.tool_results:
                    logger.info(f"✅ Tool returned result.")
                else:
                    logger.info(f"⚙️ Agent Event: Processing step...")

                if hasattr(event, "output") and event.output:
                    final_output = event.output
                elif hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            full_text += part.text
            
            if not final_output and full_text:
                try:
                    clean_val = full_text.strip().strip("```json").strip("```").strip()
                    final_output = json.loads(clean_val)
                except:
                    final_output = full_text
            
            if not final_output:
                raise ValueError("Failed to produce structured output.")
            
            if isinstance(final_output, dict):
                return ReviewSynthesizerOutput(**final_output)
            return final_output
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise ValueError(f"Review Summarizer failed: {e}")
        finally:
            await self.runner.session_service.delete_session(
                app_name=self.runner.app_name,
                user_id="default_user",
                session_id=session_id
            )
