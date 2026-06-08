import json
import os
import sys
import asyncio
import logging
import argparse
import traceback
import nest_asyncio
import urllib.parse
import urllib.request
from typing import List

import pydantic
from google.adk import Agent

# Fix sys.path for standalone or server execution
_agents_dir = os.path.dirname(os.path.abspath(__file__))
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)
_util_dir = os.path.join(_agents_dir, "agent-util")
if _util_dir not in sys.path:
    sys.path.insert(0, _util_dir)

from youtube_summarizer import YouTubeSummarizer
from itinerary_planner import ItineraryPlanner
from review_summarizer import ReviewSummarizer
from location_navigation import LocationNavigationAgent
from config_utils import load_config

# Set up standard logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Orchestrator")


class TravelPlannerOrchestrator:
    def __init__(self):
        self.config_data = load_config()
        
        # We extract keys explicitly via DI, but ADK requires environment variables
        gemini_key = self.config_data.get("apiKeys", {}).get("gemini")
        maps_key = self.config_data.get("apiKeys", {}).get("maps")
        youtube_key = self.config_data.get("apiKeys", {}).get("youtube")
        
        if gemini_key:
            os.environ["GOOGLE_API_KEY"] = gemini_key
            os.environ["GEMINI_API_KEY"] = gemini_key
        if maps_key:
            os.environ["GOOGLE_MAPS_API_KEY"] = maps_key

        self.gemini_model = self.config_data.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-3.5-flash")
        
        # Instantiate all agents declaratively and safely
        self.summarizer = YouTubeSummarizer(youtube_key=youtube_key, gemini_key=gemini_key, model_id=self.gemini_model)
        self.planner = ItineraryPlanner(maps_key=maps_key, model_id=self.gemini_model)
        self.reviewer = ReviewSummarizer(maps_key=maps_key, model_id=self.gemini_model)
        self.location_agent = LocationNavigationAgent(maps_key=maps_key, gemini_key=gemini_key, model_id=self.gemini_model)

    def query(self, video_url: str, intent_query: str) -> dict:
        """Entry point for Gemini Enterprise Agent Platform (Reasoning Engine)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            nest_asyncio.apply()
            return loop.run_until_complete(self.coordinate_plan(video_url, intent_query))
        else:
            return asyncio.run(self.coordinate_plan(video_url, intent_query))

    async def coordinate_plan(self, video_url: str, intent_query: str) -> dict:
        logger.info(f"Starting coordinated multi-agent sequence...")
        logger.info(f"YouTube URL: {video_url}")
        logger.info(f"User Intent: {intent_query}")

        # 🚀 STAGE 1: SUMMARIZE YOUTUBE
        logger.info("Engaging Stage 1: YouTube Summarizer Agent...")
        summarizer_output = await self.summarizer.summarize(video_url)
        logger.info(f"Stage 1 complete. Video Title: '{summarizer_output.title}'")

        # 🚀 STAGE 2: PLAN CUSTOM ITINERARY
        logger.info("Engaging Stage 2: Itinerary Planner Agent...")
        planner_output = await self.planner.plan(summarizer_output.model_dump() if hasattr(summarizer_output, 'model_dump') else summarizer_output, intent_query)
        logger.info(f"Stage 2 complete. Generated '{planner_output.title}' itinerary.")

        # 🚀 STAGE 3: SUMMARIZE REVIEWS
        logger.info("Engaging Stage 3: Review Summarizer Agent...")
        places_to_review = []
        for hotel in planner_output.hotels:
            if hotel.place_id:
                places_to_review.append({"place_id": hotel.place_id, "name": hotel.name, "category": "Hotel"})

        for day in planner_output.days:
            for item in day.items:
                if item.type == "food" and item.title:
                    places_to_review.append({"place_id": "", "name": item.title, "category": "Dining"})

        unique_places = []
        seen = set()
        for p in places_to_review:
            if p["name"] not in seen:
                seen.add(p["name"])
                unique_places.append(p)
        unique_places = unique_places[:4]

        reviews_output = await self.reviewer.summarize_reviews(unique_places, intent_query)
        logger.info("Stage 3 complete. Review synthesis compiled.")

        # 🚀 STAGE 4: AGGREGATE UNIFIED OUTPUT
        planner_data = planner_output.model_dump() if hasattr(planner_output, "model_dump") else planner_output
        
        # Enrich hotels with nearby attractions in parallel
        hotels_list = planner_data.get("hotels", [])
        await self.location_agent.enrich_hotels_with_attractions(hotels_list, intent_query)

        aggregated_result = {
            "youtube_details": summarizer_output.model_dump() if hasattr(summarizer_output, 'model_dump') else summarizer_output,
            "custom_itinerary": planner_data,
            "grounded_reviews": reviews_output.model_dump() if hasattr(reviews_output, 'model_dump') else reviews_output
        }

        # Generate markdown report content
        report_md = self._generate_markdown_report(video_url, intent_query, aggregated_result)
        aggregated_result["report_md"] = report_md
        
        return aggregated_result

    def _generate_markdown_report(self, video_url: str, intent_query: str, data: dict) -> str:
        yt = data["youtube_details"]
        plan = data["custom_itinerary"]
        revs = data["grounded_reviews"]

        markdown_content = f"""# Aura Voyage 🧭 — Multi-Agent Coordinated Itinerary Report

## 📹 Inspirational Source Context (YouTube Grounding)
* **Video Title**: {yt["title"]}
* **Creator**: {yt["author"]}
* **URL**: [{video_url}]({video_url})

> **chronological Travel Notes**:
> {yt["itinerary_notes"]}

---

## 🎯 User Planning Customization & Intent
* **Specified Intent / Style**: `"{intent_query}"`
* **Itinerary Compile**: `{plan["title"]}`
* **Style Pitch**: *"{plan["subtitle"]}"*

---

## 🏨 Concrete Lists of Hotels (Satisfying user's exact intent)
"""
        for h in plan["hotels"]:
            markdown_content += f"### 🏢 {h['name']}\n"
            markdown_content += f"* **Address**: {h['address']}\n"
            markdown_content += f"* **Places Details Rating**: `⭐ {h['rating']}/5`\n"
            markdown_content += f"* **Planner Context**: {h['description']}\n\n"

            match_review = next((r for r in revs["summaries"] if r["name"] == h["name"] or r["place_id"] == h["place_id"]), None)
            if match_review:
                markdown_content += f"> #### 💬 Verified Reviews Summary\n"
                markdown_content += f"> {match_review['reviews_summary']}\n"
                markdown_content += f">\n"
                markdown_content += f"> **Highlights**:\n"
                for highlight in match_review["key_highlights"]:
                    markdown_content += f"> * {highlight}\n"
                markdown_content += f">\n"
                markdown_content += f"> **Suitability Analysis**:\n"
                markdown_content += f"> {match_review['suitability_analysis']}\n\n"

        markdown_content += "\n--- \n\n## 📅 Day-by-Day Itinerary\n"
        for day in plan["days"]:
            markdown_content += f"### Day {day['day']}: {day['summary']}\n"
            for item in day["items"]:
                markdown_content += f"* **{item['time']}** - **{item['title']}** (`{item['type'].upper()}`)\n"
                markdown_content += f"  *Description*: {item['description']}\n"
                if item["swaps"]:
                    markdown_content += f"  *Interactive Swaps Available*: `{', '.join(item['swaps'])}`\n"
            markdown_content += "\n"

        return markdown_content


async def main():
    parser = argparse.ArgumentParser(description="Aura Voyage Coordinated Multi-Agent Travel Orchestrator")
    parser.add_argument("--url", type=str, default="https://www.youtube.com/watch?v=f4wBcKc2j8s", help="YouTube travel video URL")
    parser.add_argument("--intent", type=str, default="plan me a family friendly trip", help="User trip style planning intent")
    args = parser.parse_args()

    orchestrator = TravelPlannerOrchestrator()
    
    try:
        result = await orchestrator.coordinate_plan(args.url, args.intent)
        print(f"\n=========================================================")
        print(f"🎉 SUCCESS: Multi-Agent Coordinated Trip Plan Compiled!")
        print(f"Title: {result['custom_itinerary']['title']}")
        print(f"=========================================================\n")
        
        # Optionally write local file if running locally
        outputs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_single_agent_outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        report_path = os.path.join(outputs_dir, "tuscany_coordinated_family_trip.md")
        with open(report_path, "w") as f:
            f.write(result["report_md"])
        print(f"Report saved to: {report_path}")

    except Exception as e:
        logger.error(f"Orchestrator execution failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
