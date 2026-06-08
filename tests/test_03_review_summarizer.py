import sys
import os
import json
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents/agent-util')))

from review_summarizer import ReviewSummarizer
from config_utils import load_config

class TestReviewSummarizer(unittest.IsolatedAsyncioTestCase):
    async def test_summarize_reviews(self):
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

        places_to_review = []
        for hotel in planner_output.get("hotels", []):
            if hotel.get("place_id"):
                places_to_review.append({"place_id": hotel["place_id"], "name": hotel["name"], "category": "Hotel"})
                
        # Just grab max 2 to keep tests fast
        places_to_review = places_to_review[:2]
        
        if not places_to_review:
            self.skipTest("No places with place_id found in planner output")

        reviewer = ReviewSummarizer(maps_key, model_id)
        intent_query = "plan me a family friendly trip"
        
        result = await reviewer.summarize_reviews(places_to_review, intent_query)
        self.assertIsNotNone(result)
        
        output_dict = result.model_dump() if hasattr(result, "model_dump") else result
        
        out_fixture = os.path.join(os.path.dirname(__file__), "fixtures", "stage3_reviews.json")
        with open(out_fixture, "w") as f:
            json.dump(output_dict, f, indent=2)
            
        self.assertIn("summaries", output_dict)

if __name__ == "__main__":
    unittest.main()
