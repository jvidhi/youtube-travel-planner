import sys
import os
import json
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents/agent-util')))

from orchestrator import TravelPlannerOrchestrator
from config_utils import load_config

class TestOrchestratorE2E(unittest.IsolatedAsyncioTestCase):
    async def test_e2e_flow(self):
        config = load_config()
        maps_key = config.get("apiKeys", {}).get("maps")
        gemini_key = config.get("apiKeys", {}).get("gemini")
        youtube_key = config.get("apiKeys", {}).get("youtube")
        
        if not maps_key or not gemini_key or not youtube_key:
            self.skipTest("Missing API keys for E2E test")
            
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["GOOGLE_API_KEY"] = gemini_key
        os.environ["GOOGLE_MAPS_API_KEY"] = maps_key

        orchestrator = TravelPlannerOrchestrator()
        
        # We use a short/fast travel video to ensure tests run reasonably quickly
        video_url = "https://www.youtube.com/watch?v=f4wBcKc2j8s"
        intent_query = "plan me a family friendly trip"
        
        # Test full pipeline
        result = await orchestrator.coordinate_plan(video_url, intent_query)
        
        self.assertIsNotNone(result)
        self.assertIn("custom_itinerary", result)
        self.assertIn("report_md", result)
        self.assertTrue(len(result["report_md"]) > 100)
        
        # Save final output
        out_fixture = os.path.join(os.path.dirname(__file__), "fixtures", "stage5_final_e2e.json")
        with open(out_fixture, "w") as f:
            json.dump(result, f, indent=2)

if __name__ == "__main__":
    unittest.main()
