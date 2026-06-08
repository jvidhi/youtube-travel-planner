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
from agent_hooks import before_tool_callback, after_tool_callback, on_tool_error_callback

logger = logging.getLogger("LocationNavigation")

class Attraction(pydantic.BaseModel):
    name: str
    rating: str
    vicinity: str

class RankedAttractions(pydantic.BaseModel):
    attractions: List[Attraction]

class LocationNavigationAgent:
    def __init__(self, maps_key: str, gemini_key: str, model_id: str = "gemini-3.5-flash"):
        self.maps_key = maps_key
        self.gemini_key = gemini_key
        self.gemini_model = model_id
        
        sys_instructions = (
            "You are a travel concierge. Your goal is to select the top 3 most relevant tourist attractions "
            "from a provided list based on the user's travel intent. "
            "Prioritize attractions that perfectly match the vibe (e.g., child-friendly for families, "
            "nightlife/excitement for bachelor parties, quiet/scenic for couples)."
        )

        self.agent = Agent(
            name="concierge_agent",
            model=self.gemini_model,
            instruction=sys_instructions,
            output_schema=RankedAttractions,
            before_tool_callback=before_tool_callback,
            after_tool_callback=after_tool_callback,
            on_tool_error_callback=on_tool_error_callback
        )
        self.runner = InMemoryRunner(agent=self.agent)

    async def fetch_nearby_attractions(self, place_id: str, intent_query: str) -> dict:
        """Fetches neighborhood attractions for a given hotel place_id and ranks them by intent using Gemini."""
        logger.info(f"🔧 Tool execution: fetch_nearby_attractions(place_id='{place_id}', intent_query='{intent_query}')")
        
        if not self.maps_key:
            return {"error": "Google Maps API Key missing"}

        try:
            # 1. Get Geometry of the Place
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=geometry&key={self.maps_key}"
            req1 = urllib.request.Request(details_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req1) as res1:
                details_data = json.loads(res1.read().decode())
                location = details_data.get("result", {}).get("geometry", {}).get("location")
                if not location:
                    return {"error": "Could not fetch location for place_id"}
            
            # 2. Search nearby attractions
            lat, lng = location["lat"], location["lng"]
            nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=2000&type=tourist_attraction&key={self.maps_key}"
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

                prompt = (
                    f"User Intent: {intent_query}\n\n"
                    f"Raw Nearby Attractions List:\n{json.dumps(raw_attractions, indent=2)}\n\n"
                    f"Please select and return exactly the top 3 most suitable attractions matching this intent."
                )
                
                logger.info(f"🧠 Prompting Gemini Model ({self.gemini_model}) to rank attractions for place_id='{place_id}'...")

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
                        # Observability
                        if hasattr(event, "tool_calls") and event.tool_calls:
                            logger.info(f"🔧 Agent is calling tool.")
                        elif hasattr(event, "tool_results") and event.tool_results:
                            logger.info(f"✅ Tool returned result.")
                        else:
                            logger.info(f"⚙️ Agent Event: Processing step...")

                        # Strict output parsing
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
                        return final_output
                    elif hasattr(final_output, "model_dump"):
                        return final_output.model_dump()
                    else:
                        return {"attractions": raw_attractions[:3]}
                except Exception as e:
                    logger.warning(f"Fallback to raw attractions due to agent failure: {e}")
                    return {"attractions": raw_attractions[:3]}
                finally:
                    await self.runner.session_service.delete_session(
                        app_name=self.runner.app_name,
                        user_id="default_user",
                        session_id=session_id
                    )

        except Exception as e:
            logger.error(f"Nearby attraction ranking failed: {e}")
            return {"error": str(e)}

    async def enrich_hotels_with_attractions(self, hotels_list: list, intent_query: str):
        logger.info("Enriching hotels with nearby attractions...")
        hotel_tasks = []
        for hotel in hotels_list:
            place_id = hotel.get("place_id")
            if place_id:
                hotel_tasks.append(self.fetch_nearby_attractions(place_id, intent_query))
            else:
                hotel_tasks.append(asyncio.sleep(0, result={"attractions": []}))

        nearby_results = await asyncio.gather(*hotel_tasks)
        
        for i, hotel in enumerate(hotels_list):
            res = nearby_results[i]
            if isinstance(res, dict):
                hotel["nearby_attractions"] = res.get("attractions", [])
            else:
                hotel["nearby_attractions"] = []
        return hotels_list
