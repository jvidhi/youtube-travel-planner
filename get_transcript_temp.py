import json
from youtube_transcript_api import YouTubeTranscriptApi

video_id = "YWo6-EU0m-g"
try:
    transcript_list = YouTubeTranscriptApi().fetch(video_id).to_raw_data()
    full_text = ""
    lines = []
    for entry in transcript_list:
        start_sec = int(entry['start'])
        minutes = start_sec // 60
        seconds = start_sec % 60
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        line = f"{timestamp} {entry['text']}"
        lines.append(line)
        full_text += entry['text'] + " "

    res = {
        "video_id": video_id,
        "transcript_text": full_text.strip(),
        "chronological_transcript": "\n".join(lines)
    }
    with open("transcript_output.json", "w") as f:
        json.dump(res, f, indent=2)
    print("SUCCESS")
except Exception as e:
    with open("transcript_error.txt", "w") as f:
        f.write(str(e))
    print("ERROR:", e)
