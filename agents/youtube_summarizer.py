import json
import os
import re
import uuid
import urllib.parse
import urllib.request
import asyncio
import logging
import pydantic
from typing import List, Optional

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from google import genai

from config_utils import load_config
from agent_hooks import before_tool_callback, after_tool_callback, on_tool_error_callback

logger = logging.getLogger("YouTubeSummarizer")


# ==========================================
# 📋 SCHEMAS FOR STRUCTURED OUTPUT
# ==========================================

class Place(pydantic.BaseModel):
    name: str
    category: str  # e.g., "Sightseeing", "Dining", "Hotel", "Transit", "Activity"
    description: str
    vibe: str       # e.g., "Chill", "Vibrant", "Cultural", "Adventure", "Historic"

class Hotel(pydantic.BaseModel):
    name: str
    budget_tier: str  # "Budget 🎒", "Moderate 💳", "Luxury 💎"
    details: str

class Tip(pydantic.BaseModel):
    topic: str        # e.g., "Transit", "Connectivity", "Local Custom", "Packing"
    content: str

class SummarizerOutput(pydantic.BaseModel):
    title: str
    author: str
    places: List[Place]
    hotels: List[Hotel]
    tips: List[Tip]
    itinerary_notes: str


# ==========================================
# 🛠️ CUSTOM TOOLS FOR ANTIGRAVITY AGENT
# ==========================================

def extract_youtube_id(url: str) -> str:
    """Extract the 11-character YouTube Video ID from a URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed.path.strip('/')
    if parsed.hostname in ('youtube.com', 'www.youtube.com'):
        if parsed.path == '/watch':
            p = urllib.parse.parse_qs(parsed.query)
            return p.get('v', [''])[0]
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/')[2]
        if parsed.path.startswith('/v/'):
            return parsed.path.split('/')[2]
    return ""


def get_youtube_video_details(video_url: str) -> str:
    """Queries the YouTube Data API to extract video snippet metadata details.
    
    Args:
        video_url: The YouTube URL to query.
    """
    logger.info(f"🔧 Tool execution: get_youtube_video_details(video_url='{video_url}')")
    video_id = extract_youtube_id(video_url)
    if not video_id:
        return json.dumps({"error": "Invalid YouTube URL"})

    config = load_config()
    api_key = config.get("apiKeys", {}).get("youtube")
    if not api_key:
        return json.dumps({"error": "YouTube API Key is missing in config.json"})

    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data.get("items"):
                snippet = data["items"][0]["snippet"]
                return json.dumps({
                    "video_id": video_id,
                    "title": snippet.get("title"),
                    "channel": snippet.get("channelTitle"),
                    "description": snippet.get("description"),
                    "tags": snippet.get("tags", []),
                    "published_at": snippet.get("publishedAt")
                }, indent=2)
            return json.dumps({"error": f"Video {video_id} not found"})
    except Exception as e:
        return json.dumps({"error": f"YouTube API query failed: {str(e)}"})


def get_youtube_video_transcript(video_url: str) -> str:
    """Retrieves the chronological subtitles & text transcript from the video.
    
    Args:
        video_url: The YouTube URL to retrieve.
    """
    logger.info(f"🔧 Tool execution: get_youtube_video_transcript(video_url='{video_url}')")
    video_id = extract_youtube_id(video_url)
    if not video_id:
        return json.dumps({"error": "Invalid YouTube URL"})

    try:
        config = load_config()
        api_key = config.get("apiKeys", {}).get("youtube")
        if not api_key:
            raise ValueError("YouTube API Key is missing in config.json")

        # 1. List caption tracks
        list_url = f"https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={api_key}"
        req = urllib.request.Request(list_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            captions_data = json.loads(response.read().decode())
        
        items = captions_data.get("items", [])
        if not items:
            raise ValueError(f"No captions found for video {video_id}")

        # Prefer manual captions over auto-generated if possible
        # Or just pick the first one for now as a baseline
        caption_id = items[0]["id"]
        
        # 2. Download the caption track
        # Note: Official API download often requires OAuth2 for non-owned videos.
        # We try it, but expect it might fail for many public videos.
        download_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=vtt&key={api_key}"
        download_req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(download_req) as response:
            transcript_vtt = response.read().decode()

        # Simple VTT parsing to extract text and timestamps
        lines = []
        full_text = ""
        current_timestamp = ""
        
        for line in transcript_vtt.split("\n"):
            line = line.strip()
            if "-->" in line:
                # Extract start time (HH:MM:SS.mmm)
                start_time_str = line.split("-->")[0].strip()
                # Convert to [MM:SS]
                parts = start_time_str.split(":")
                if len(parts) >= 2:
                    try:
                        hours = int(parts[0]) if len(parts) == 3 else 0
                        mins = int(parts[-2])
                        secs = float(parts[-1])
                        total_mins = hours * 60 + mins
                        current_timestamp = f"[{total_mins:02d}:{int(secs):02d}]"
                    except:
                        current_timestamp = ""
            elif line and not line.isdigit() and not line.startswith("WEBVTT"):
                if current_timestamp:
                    line_with_ts = f"{current_timestamp} {line}"
                    lines.append(line_with_ts)
                    current_timestamp = "" # Only apply timestamp to the next line once
                else:
                    # If it's a multi-line caption, just append the text
                    if lines:
                        lines[-1] += " " + line
                full_text += line + " "

        return json.dumps({
            "video_id": video_id,
            "transcript_text": full_text.strip(),
            "chronological_transcript": "\n".join(lines),
            "note": "Retrieved via official YouTube Data API (captions resource)."
        }, indent=2)
    except Exception as e:
        logger.warning(f"Official YouTube Captions API failed: {e}. Falling back to Gemini multimodal video parsing.")
        try:
            config_data = load_config()
            gemini_key = config_data.get("apiKeys", {}).get("gemini", "")
            if not gemini_key:
                return json.dumps({"error": "Gemini API key missing for fallback video parsing."})
            
            client = genai.Client(api_key=gemini_key)
            
            gemini_model = config_data.get("models", {}).get("gemini", {}).get("activeModelId", "gemini-3.5-flash")
            
            # Use the configured model for video understanding capabilities
            # For youtube links, we can pass it as a Part using from_uri or directly in the prompt if the model supports YouTube URLs.
            # In the new genai SDK, we can pass the YouTube video as a file-like uri if supported, or just pass the URL in the text.
            # However, the standard way for YouTube videos in GenAI is to pass the URL.
            response = client.models.generate_content(
                model=gemini_model,
                contents=[
                    f"Watch this YouTube video: {video_url}\n\n"
                    "Provide a detailed chronological transcript and summary of the video, including timestamps if possible, "
                    "focusing on the places visited, hotels, and travel tips mentioned."
                ]
            )
            
            return json.dumps({
                "video_id": video_id,
                "transcript_text": response.text,
                "chronological_transcript": response.text,
                "note": "This transcript was generated by Gemini Multimodal fallback."
            }, indent=2)
        except Exception as fallback_err:
            return json.dumps({"error": f"Failed to fetch transcript and Gemini fallback failed: {str(fallback_err)}"})


# ==========================================
# 🧭 SUMMARIZER AGENT CLASS
# ==========================================

class YouTubeSummarizer:
    def __init__(self, model_id: str = "gemini-3.5-flash"):
        self.gemini_model = model_id
        
        sys_instructions = (
            "You are an expert YouTube Travel Summarizer. Your goal is to extract all landmarks, "
            "hotel opportunities, and connectivity/transit tips from the provided video snippet and transcript."
        )

        self.agent = Agent(
            name="youtube_summarizer",
            model=self.gemini_model,
            instruction=sys_instructions,
            output_schema=SummarizerOutput,
            before_tool_callback=before_tool_callback,
            after_tool_callback=after_tool_callback,
            on_tool_error_callback=on_tool_error_callback
        )
        self.runner = InMemoryRunner(agent=self.agent)

    async def summarize(self, video_url: str) -> SummarizerOutput:
        logger.info(f"Summarizer engaging for travel video: {video_url}")
        
        # Step 1: Fetch video details first to get title and channel for caching
        logger.info(f"🚀 Fetching YouTube metadata to check transcript cache...")
        loop = asyncio.get_running_loop()
        video_details = await loop.run_in_executor(None, get_youtube_video_details, video_url)
        
        try:
            details_obj = json.loads(video_details)
            title = details_obj.get("title", "Unknown_Title")
            channel = details_obj.get("channel", "Unknown_Channel")
        except:
            title = "Unknown_Title"
            channel = "Unknown_Channel"

        def sanitize_filename(name):
            return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
            
        safe_title = sanitize_filename(title)
        safe_channel = sanitize_filename(channel)
        cache_filename = f"{safe_title}__by__{safe_channel}_transcript.json"
        
        # We assume sample_single_agent_outputs is one directory up if agents/ is our cwd,
        # but let's make it relative to the project root (where this is usually run from).
        # We can dynamically resolve relative to the script location.
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(base_dir, "sample_single_agent_outputs")
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_filepath = os.path.join(cache_dir, cache_filename)

        if os.path.exists(cache_filepath):
            logger.info(f"✅ Found cached transcript: {cache_filename}")
            with open(cache_filepath, "r", encoding="utf-8") as f:
                video_transcript = f.read()
        else:
            logger.info(f"🚀 Cache miss. Fetching YouTube transcript...")
            video_transcript = await loop.run_in_executor(None, get_youtube_video_transcript, video_url)
            with open(cache_filepath, "w", encoding="utf-8") as f:
                f.write(video_transcript)
            logger.info(f"✅ Saved new transcript to cache: {cache_filename}")
        
        logger.info(f"✅ Video Context Ready. Compiling AI Summary...")

        prompt = (
            f"Please extract all travel destinations, hotel details, practical tips, "
            f"and a grounded chronological travel summary for this video: {video_url}.\n\n"
            f"### VIDEO METADATA ###\n{video_details}\n\n"
            f"### VIDEO TRANSCRIPT ###\n{video_transcript}\n\n"
            f"Compile structural elements matching the required output schema strictly based on the context above."
        )
        logger.info(f"🧠 Prompting Gemini Model ({self.gemini_model}) for structured travel synthesis...")
        
        try:
            # ADK requires explicit session creation
            session_id = f"sess_{uuid.uuid4()}"
            await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="default_user",
                session_id=session_id
            )
            
            # Since ADK returns an AsyncGenerator of Events, we need to gather the output
            # A common pattern is to just collect the final OUTPUT event.
            final_output = None
            msg = Content(role="user", parts=[Part.from_text(text=prompt)])
            async for event in self.runner.run_async(user_id="default_user", session_id=session_id, new_message=msg):
                logger.info(f"⚙️  Agent Event: Processing step in youtube_summarizer...")
                # ADK events usually contain output in event.output when event.type == "OUTPUT"
                # but to be safe we can check for output attribute.
                if hasattr(event, "output") and event.output:
                    final_output = event.output
                elif hasattr(event, "content") and event.content and event.content.parts:
                    text_val = event.content.parts[0].text
                    if text_val:
                        
                        try:
                            final_output = json.loads(text_val)
                        except:
                            final_output = text_val
            
            structured_data = final_output
            
            if not structured_data:
                raise ValueError("YouTube Summarizer failed to produce structured output.")
            
            if isinstance(structured_data, dict):
                return SummarizerOutput(**structured_data)
            return structured_data
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise ValueError(f"YouTube Summarizer failed: {e}")
