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

logger = logging.getLogger("ItineraryPlanner")


# ==========================================
# 📋 SCHEMAS FOR STRUCTURED OUTPUT
# ==========================================

class RealPlace(pydantic.BaseModel):
    id: str
    name: str
    category: str
    desc: str
    lat: float
    lng: float

class RealHotel(pydantic.BaseModel):
    id: str
    name: str
    address: str
    rating: float
    place_id: str
    description: str

class RealActivity(pydantic.BaseModel):
    id: str
    time: str
    title: str
    type: str  # e.g. "place", "food", "activity"
    refId: Optional[str] = None
    description: str
    swaps: Optional[List[str]] = []  # list of custom regional alternative sights/restaurants

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


# ==========================================
# 🛠️ CUSTOM TOOLS FOR ANTIGRAVITY AGENT
# ==========================================

def google_places_hotel_search(destination: str, intent: str) -> str:
    """Queries the Google Places Text Search API to find real, operational hotels matching the user's intent.
    
    Args:
        destination: The city/region to search hotels in (e.g. 'Pienza', 'Montalcino').
        intent: The user's trip style intent (e.g. 'family friendly', 'luxury couple resort', 'romantic').
        
    Returns:
        JSON string representing a list of real hotels with place IDs, ratings, addresses, and location coordinates.
    """
    config = load_config()
    api_key = config.get("apiKeys", {}).get("maps")
    if not api_key:
        return json.dumps({"error": "Google Maps API Key is missing in config.json"})

    search_query = f"{intent} hotels in {destination} Tuscany"
    encoded_query = urllib.parse.quote(search_query)
    api_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={api_key}"
    
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            results = []
            if data.get("results"):
                for item in data["results"][:4]:  # Top 4 operational results
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


def google_places_restaurant_search(destination: str, intent: str) -> str:
    """Queries the Google Places Text Search API to find real, highly rated restaurants or cafes in a destination.
    
    Args:
        destination: The city or town in Tuscany (e.g. 'Pienza', 'Montepulciano').
        intent: The target styling focus (e.g. 'kid-friendly dining', 'local steakhouse', 'romantic scenic dinner').
    """
    config = load_config()
    api_key = config.get("apiKeys", {}).get("maps")
    if not api_key:
        return json.dumps({"error": "Google Maps API Key is missing in config.json"})

    search_query = f"{intent} restaurants in {destination} Tuscany"
    encoded_query = urllib.parse.quote(search_query)
    api_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={api_key}"
    
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


# ==========================================
# 🧭 ITINERARY PLANNER AGENT CLASS
# ==========================================

class ItineraryPlanner:
    def __init__(self):
        self.config_data = load_config()
        self.gemini_key = self.config_data.get("apiKeys", {}).get("gemini", "")
        self.gemini_model = self.config_data.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-2.5-flash")

    async def plan(self, summarizer_output: dict, intent_query: str) -> ItineraryOutput:
        logger.info(f"Itinerary Planner engaging for intent: {intent_query}")
        
        sys_instructions = (
            "You are an advanced AI Travel Planner. Your goal is to compile a highly polished "
            "itinerary matching the user's planning intent (e.g., 'plan me a family friendly trip'). "
            "To do this, you MUST call your Google Places tools ('google_places_hotel_search' and 'google_places_restaurant_search') "
            "to fetch REAL, highly-rated, and currently operational hotels, restaurants, and dining stops "
            "in the specific cities/regions parsed from the YouTube summary context. "
            "Never output placeholders or mock coordinates. You MUST match real locations, address markers, and geometries "
            "so they can be plotted accurately on visual maps downstream."
        )

        agent_config = LocalAgentConfig(
            model=self.gemini_model,
            api_key=self.gemini_key,
            system_instructions=sys_instructions,
            tools=[google_places_hotel_search, google_places_restaurant_search],
            response_schema=ItineraryOutput
        )

        # Prepare grounding context from summarizer output
        grounding_context = json.dumps(summarizer_output, indent=2)

        async with Agent(config=agent_config) as agent:
            prompt = (
                f"Please build a complete, highly targeted travel itinerary customized to this User Intent:\n"
                f"\"**{intent_query}**\"\n\n"
                f"Grounding travel details from YouTube video:\n"
                f"{grounding_context}\n\n"
                f"You MUST:\n"
                f"1. Identify the core destinations from the video notes (e.g. Pienza, Montalcino, Val d'Orcia).\n"
                f"2. Call 'google_places_hotel_search' for each town using the user's intent (e.g., family friendly, kid safe) to retrieve actual hotels.\n"
                f"3. Call 'google_places_restaurant_search' for dining recommendations aligned with their intent.\n"
                f"4. Construct a day-by-day itinerary. In each activity, match the locations, coordinates, ratings, and place IDs discovered."
            )
            
            response = await agent.chat(prompt)
            structured_data = await response.structured_output()
            if not structured_data:
                raise ValueError("Itinerary Planner failed to produce structured output.")
            return ItineraryOutput(**structured_data)
