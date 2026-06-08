import sys
import os
import json
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents/agent-util')))

from itinerary_planner import ItineraryPlanner
from config_utils import load_config

class TestItineraryPlanner(unittest.IsolatedAsyncioTestCase):
    async def test_plan(self):
        config = load_config()
        maps_key = config.get("apiKeys", {}).get("maps")
        gemini_key = config.get("apiKeys", {}).get("gemini")
        model_id = config.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-3.5-flash")
        
        if not maps_key or not gemini_key:
            self.skipTest("Missing API keys")
            
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["GOOGLE_API_KEY"] = gemini_key

        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "stage1_youtube.json")
        if not os.path.exists(fixture_path):
            self.fail("Prerequisite fixture stage1_youtube.json not found. Run test_01 first.")
            
        with open(fixture_path, "r") as f:
            summarizer_output = json.load(f)

        planner = ItineraryPlanner(maps_key, model_id)
        intent_query = "plan me a family friendly trip"
        
        result = await planner.plan(summarizer_output, intent_query)
        self.assertIsNotNone(result)
        
        output_dict = result.model_dump() if hasattr(result, "model_dump") else result
        
        # Save output for next test
        out_fixture = os.path.join(os.path.dirname(__file__), "fixtures", "stage2_itinerary.json")
        with open(out_fixture, "w") as f:
            json.dump(output_dict, f, indent=2)
            
        self.assertIn("hotels", output_dict)
        self.assertIn("days", output_dict)

if __name__ == "__main__":
    unittest.main()
