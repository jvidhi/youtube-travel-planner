import json
import os
import uuid
import asyncio
import logging
import urllib.parse
import urllib.request
from typing import List
import pydantic
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from config_utils import load_config
from agent_hooks import before_tool_callback, after_tool_callback, on_tool_error_callback

logger = logging.getLogger("LocationNavigation")

class Attraction(pydantic.BaseModel):
    name: str
    rating: str
    vicinity: str

class RankedAttractions(pydantic.BaseModel):
    attractions: List[Attraction]

async def fetch_nearby_attractions(place_id: str, intent_query: str) -> dict:
    """Fetches neighborhood attractions for a given hotel place_id and ranks them by intent using Gemini."""
    logger.info(f"🔧 Tool execution: fetch_nearby_attractions(place_id='{place_id}', intent_query='{intent_query}')")
    config = load_config()
    api_key = config.get("apiKeys", {}).get("maps")
    gemini_key = config.get("apiKeys", {}).get("gemini")
    gemini_model = config.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-3.5-flash")
    
    # Sync environment for SDKs
    if gemini_key: os.environ["GOOGLE_API_KEY"] = gemini_key
    if api_key: os.environ["GOOGLE_MAPS_API_KEY"] = api_key
    
    if not api_key:
        return {"error": "Google Maps API Key missing"}

    try:
        # 1. Get Geometry of the Place
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=geometry&key={api_key}"
        req1 = urllib.request.Request(details_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req1) as res1:
            details_data = json.loads(res1.read().decode())
            location = details_data.get("result", {}).get("geometry", {}).get("location")
            if not location:
                return {"error": "Could not fetch location for place_id"}
        
        # 2. Search nearby attractions (Fetch more to allow for better AI ranking)
        lat, lng = location["lat"], location["lng"]
        nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=2000&type=tourist_attraction&key={api_key}"
        req2 = urllib.request.Request(nearby_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2) as res2:
            nearby_data = json.loads(res2.read().decode())
            raw_attractions = []
            for item in nearby_data.get("results", [])[:15]:
                raw_attractions.append({
                    "name": item.get("name"),
                    "rating": str(item.get("rating", "N/A")),
                    "vicinity": item.get("vicinity")
                })
            
            if not raw_attractions:
                return {"attractions": []}

            # 3. Use Gemini to rank and select the top 3 based on intent
            sys_instructions = (
                f"You are a travel concierge. Your goal is to select the top 3 most relevant tourist attractions "
                f"from a provided list based on the user's travel intent: '{intent_query}'. "
                f"Prioritize attractions that perfectly match the vibe (e.g., child-friendly for families, "
                f"nightlife/excitement for bachelor parties, quiet/scenic for couples)."
            )

            agent = Agent(
                name="concierge_agent",
                model=gemini_model,
                instruction=sys_instructions,
                output_schema=RankedAttractions,
                before_tool_callback=before_tool_callback,
                after_tool_callback=after_tool_callback,
                on_tool_error_callback=on_tool_error_callback
            )

            prompt = (
                f"User Intent: {intent_query}\n\n"
                f"Raw Nearby Attractions List:\n{json.dumps(raw_attractions, indent=2)}\n\n"
                f"Please select and return exactly the top 3 most suitable attractions matching this intent."
            )
            
            logger.info(f"🧠 Prompting Gemini Model ({gemini_model}) to rank attractions for place_id='{place_id}'...")

            try:
                runner = InMemoryRunner(agent=agent)
                
                # ADK requires explicit session creation
                session_id = f"sess_{uuid.uuid4()}"
                await runner.session_service.create_session(
                    app_name=runner.app_name,
                    user_id="default_user",
                    session_id=session_id
                )
                
                final_output = None
                msg = Content(role="user", parts=[Part.from_text(text=prompt)])
                async for event in runner.run_async(user_id="default_user", session_id=session_id, new_message=msg):
                    logger.info(f"⚙️  Agent Event: Processing step in concierge_agent...")
                    if hasattr(event, "output") and event.output:
                        final_output = event.output
                    elif hasattr(event, "content") and event.content and event.content.parts:
                        text_val = event.content.parts[0].text
                        if text_val:
                            try:
                                final_output = json.loads(text_val)
                            except:
                                final_output = text_val
                
                ranked_data = final_output
                
                if isinstance(ranked_data, dict):
                    return ranked_data
                elif hasattr(ranked_data, "model_dump"):
                    return ranked_data.model_dump()
                else:
                    return {"attractions": raw_attractions[:3]}
            except Exception as e:
                logger.warning(f"Fallback to raw attractions due to agent failure: {e}")
                return {"attractions": raw_attractions[:3]}

    except Exception as e:
        logger.error(f"Nearby attraction ranking failed: {e}")
        return {"error": str(e)}

async def enrich_hotels_with_attractions(hotels_list: list, intent_query: str):
    """Enriches a list of hotels with nearby attractions in parallel."""
    logger.info("Enriching hotels with nearby attractions...")
    hotel_tasks = []
    
    for hotel in hotels_list:
        place_id = hotel.get("place_id")
        if place_id:
            hotel_tasks.append(fetch_nearby_attractions(place_id, intent_query))
        else:
            hotel_tasks.append(asyncio.sleep(0, result={"attractions": []})) # dummy task

    nearby_results = await asyncio.gather(*hotel_tasks)
    
    for i, hotel in enumerate(hotels_list):
        res = nearby_results[i]
        if isinstance(res, dict):
            hotel["nearby_attractions"] = res.get("attractions", [])
        else:
            hotel["nearby_attractions"] = []
    
    return hotels_list
