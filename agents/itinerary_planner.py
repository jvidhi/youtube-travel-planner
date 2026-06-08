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

logger = logging.getLogger("ItineraryPlanner")

class RealPlace(pydantic.BaseModel):
    id: str
    name: str = "Unknown Place"
    category: str = "Location"
    desc: str = ""
    lat: float = 0.0
    lng: float = 0.0
    sources: List[str] = ["youtube"]

class RealHotel(pydantic.BaseModel):
    id: str
    name: str
    address: str
    rating: float
    place_id: str
    description: str
    sources: List[str]

class RealActivity(pydantic.BaseModel):
    id: str
    time: str
    title: str
    type: str
    refId: Optional[str] = None
    description: str
    swaps: Optional[List[str]] = []
    sources: List[str] 

class RealDay(pydantic.BaseModel):
    day: int
    summary: str
    items: List[RealActivity]

class ItineraryOutput(pydantic.BaseModel):
    title: str
    subtitle: str
    places: List[RealPlace]
    hotels: List[RealHotel]
    days: List[RealDay]

class ItineraryPlanner:
    def __init__(self, maps_key: str, model_id: str = "gemini-3.5-flash"):
        self.maps_key = maps_key
        self.gemini_model = model_id
        
        sys_instructions = (
            "You are an advanced AI Travel Planner. Your goal is to compile a highly polished "
            "itinerary matching the user's planning intent. "
            "To do this, you MUST call your Google Places tools ('google_places_hotel_search' and 'google_places_restaurant_search') "
            "to fetch REAL, highly-rated, and currently operational hotels, restaurants, and dining stops.\n\n"
            "### SOURCE TRACKING ###\n"
            "You MUST track the source of every entity in the 'sources' field:\n"
            "- If an entity was originally provided in the YouTube summary, include 'youtube' in its sources.\n"
            "- If an entity was found or verified using Google Places tools, include 'google_maps' in its sources.\n"
            "- Entities from the YouTube summary that you verify via tools should have BOTH ['youtube', 'google_maps'].\n"
            "- New entities you find via tools that were NOT in the summary should have ['google_maps'].\n"
            "EVERY entity and activity MUST have at least one source in its 'sources' list."
        )

        hotel_search_tool = FunctionTool(self.google_places_hotel_search)
        restaurant_search_tool = FunctionTool(self.google_places_restaurant_search)

        self.agent = Agent(
            name="itinerary_planner",
            model=self.gemini_model,
            instruction=sys_instructions,
            tools=[hotel_search_tool, restaurant_search_tool],
            output_schema=ItineraryOutput,
            before_tool_callback=before_tool_callback,
            after_tool_callback=after_tool_callback,
            on_tool_error_callback=on_tool_error_callback
        )
        self.runner = InMemoryRunner(agent=self.agent)

    def google_places_hotel_search(self, destination: str, intent: str) -> str:
        """Queries the Google Places Text Search API to find real, operational hotels matching the user's intent."""
        logger.info(f"🔧 Tool execution: google_places_hotel_search(destination='{destination}', intent='{intent}')")
        if not self.maps_key:
            return json.dumps({"error": "Google Maps API Key is missing"})

        search_query = f"{intent} hotels in {destination} Tuscany"
        encoded_query = urllib.parse.quote(search_query)
        api_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={self.maps_key}"
        
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                results = []
                if data.get("results"):
                    for item in data["results"][:4]:
                        results.append({
                            "name": item.get("name"),
                            "address": item.get("formatted_address"),
                            "rating": item.get("rating", 0.0),
                            "place_id": item.get("place_id"),
                            "lat": item.get("geometry", {}).get("location", {}).get("lat"),
                            "lng": item.get("geometry", {}).get("location", {}).get("lng")
                        })
                    return json.dumps(results, indent=2)
                return json.dumps({"error": "No hotels found matching query"})
        except Exception as e:
            return json.dumps({"error": f"Google Places API query failed: {str(e)}"})

    def google_places_restaurant_search(self, destination: str, intent: str) -> str:
        """Queries the Google Places Text Search API to find real, highly rated restaurants or cafes in a destination."""
        logger.info(f"🔧 Tool execution: google_places_restaurant_search(destination='{destination}', intent='{intent}')")
        if not self.maps_key:
            return json.dumps({"error": "Google Maps API Key is missing"})

        search_query = f"{intent} restaurants in {destination} Tuscany"
        encoded_query = urllib.parse.quote(search_query)
        api_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={self.maps_key}"
        
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                results = []
                if data.get("results"):
                    for item in data["results"][:4]:
                        results.append({
                            "name": item.get("name"),
                            "address": item.get("formatted_address"),
                            "rating": item.get("rating", 0.0),
                            "place_id": item.get("place_id"),
                            "lat": item.get("geometry", {}).get("location", {}).get("lat"),
                            "lng": item.get("geometry", {}).get("location", {}).get("lng")
                        })
                    return json.dumps(results, indent=2)
                return json.dumps({"error": "No restaurants found"})
        except Exception as e:
            return json.dumps({"error": f"Google Places API query failed: {str(e)}"})

    async def plan(self, summarizer_output: dict, intent_query: str) -> ItineraryOutput:
        logger.info(f"Itinerary Planner engaging for intent: {intent_query}")
        
        grounding_context = json.dumps(summarizer_output, indent=2)

        prompt = (
            f"Please build a complete, highly targeted travel itinerary customized to this User Intent:\n"
            f"\"**{intent_query}**\"\n\n"
            f"Grounding travel details from YouTube video summary:\n"
            f"{grounding_context}\n\n"
            f"You MUST:\n"
            f"1. Identify the core destinations from the video notes.\n"
            f"2. Call 'google_places_hotel_search' for each town to retrieve actual hotels.\n"
            f"3. Call 'google_places_restaurant_search' for dining recommendations.\n"
            f"4. Construct a day-by-day itinerary. Match locations, coordinates, and place IDs discovered.\n\n"
            f"### CRITICAL SCHEMA REQUIREMENT ###\n"
            f"You MUST include the 'name' field for every single item in the 'places' array.\n\n"
            f"### CRITICAL SOURCE VERIFICATION ###\n"
            f"For every Place, Hotel, and Activity, you MUST populate the 'sources' list:\n"
            f"- If the item was mentioned in the YouTube grounding context above, add 'youtube'.\n"
            f"- If the item was fetched or verified via your Google Places tools, add 'google_maps'.\n"
            f"- If an item from YouTube is verified by a tool, it MUST have BOTH: ['youtube', 'google_maps'].\n"
            f"- All final itinerary items MUST have at least one source. Do NOT hallucinate sources."
        )
        
        logger.info(f"🧠 Prompting Gemini Model ({self.gemini_model}) to generate the detailed itinerary...")
        
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
                return ItineraryOutput(**final_output)
            return final_output
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise ValueError(f"Itinerary Planner failed: {e}")
        finally:
            await self.runner.session_service.delete_session(
                app_name=self.runner.app_name,
                user_id="default_user",
                session_id=session_id
            )
