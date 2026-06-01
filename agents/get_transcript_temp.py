import sys
import json
import os

# Add venv site-packages to path just in case
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "venv", "lib", "python3.14", "site-packages"))

from youtube_transcript_api import YouTubeTranscriptApi

try:
    video_id = "YWo6-EU0m-g"
    fetched = YouTubeTranscriptApi().fetch(video_id)
    raw_data = fetched.to_raw_data()
    
    full_text = ""
    lines = []
    for entry in raw_data:
        start_sec = int(entry['start'])
        minutes = start_sec // 60
        seconds = start_sec % 60
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        line = f"{timestamp} {entry['text']}"
        lines.append(line)
        full_text += entry['text'] + " "

    result = {
        "video_id": video_id,
        "transcript_text": full_text.strip(),
        "chronological_transcript": "\n".join(lines)
    }
    with open("transcript_output.json", "w") as f:
        json.dump(result, f, indent=2)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
