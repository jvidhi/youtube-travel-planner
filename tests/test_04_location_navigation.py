import sys
import os
import json
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents/agent-util')))

from location_navigation import LocationNavigationAgent
from config_utils import load_config

class TestLocationNavigation(unittest.IsolatedAsyncioTestCase):
    async def test_enrich_hotels(self):
        config = load_config()
        maps_key = config.get("apiKeys", {}).get("maps")
        gemini_key = config.get("apiKeys", {}).get("gemini")
        model_id = config.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-3.5-flash")
        
        if not maps_key or not gemini_key:
            self.skipTest("Missing API keys")
            
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["GOOGLE_API_KEY"] = gemini_key

        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "stage2_itinerary.json")
        if not os.path.exists(fixture_path):
            self.fail("Prerequisite fixture stage2_itinerary.json not found. Run test_02 first.")
            
        with open(fixture_path, "r") as f:
            planner_output = json.load(f)

        hotels_list = planner_output.get("hotels", [])
        if not hotels_list:
            self.skipTest("No hotels found in planner output to enrich")

        location_agent = LocationNavigationAgent(maps_key, gemini_key, model_id)
        intent_query = "plan me a family friendly trip"
        
        await location_agent.enrich_hotels_with_attractions(hotels_list, intent_query)
        
        out_fixture = os.path.join(os.path.dirname(__file__), "fixtures", "stage4_enriched_hotels.json")
        with open(out_fixture, "w") as f:
            json.dump(hotels_list, f, indent=2)
            
        # Verify enrichment
        enriched = False
        for hotel in hotels_list:
            if "nearby_attractions" in hotel:
                enriched = True
                break
                
        self.assertTrue(enriched, "No hotels were enriched with nearby_attractions")

if __name__ == "__main__":
    unittest.main()
