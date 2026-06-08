import sys
import os
import json
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents/agent-util')))

from youtube_summarizer import YouTubeSummarizer
from config_utils import load_config

class TestYouTubeSummarizer(unittest.IsolatedAsyncioTestCase):
    async def test_summarize(self):
        config = load_config()
        youtube_key = config.get("apiKeys", {}).get("youtube")
        gemini_key = config.get("apiKeys", {}).get("gemini")
        model_id = config.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-3.5-flash")
        
        if not youtube_key or not gemini_key:
            self.skipTest("Missing API keys")
            
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["GOOGLE_API_KEY"] = gemini_key

        summarizer = YouTubeSummarizer(youtube_key, gemini_key, model_id)
        video_url = "https://www.youtube.com/watch?v=f4wBcKc2j8s"
        
        result = await summarizer.summarize(video_url)
        self.assertIsNotNone(result)
        
        output_dict = result.model_dump() if hasattr(result, "model_dump") else result
        
        # Save output for next test
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "stage1_youtube.json")
        with open(fixture_path, "w") as f:
            json.dump(output_dict, f, indent=2)
            
        self.assertIn("places", output_dict)
        self.assertIn("hotels", output_dict)

if __name__ == "__main__":
    unittest.main()
