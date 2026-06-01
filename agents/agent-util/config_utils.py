import os
import json
import logging

logger = logging.getLogger("ConfigUtils")

def load_config() -> dict:
    """
    Loads configuration from environment variables or a config.json file.
    Priority:
    1. Environment variables (GEMINI_API_KEY, MAPS_API_KEY, YOUTUBE_API_KEY)
    2. AGENT_CONFIG_JSON environment variable (as a JSON string)
    3. config.json in the current directory or parent directory
    """
    config = {
        "apiKeys": {},
        "models": {
            "gemini": {
                "activeModelId": os.getenv("GEMINI_MODEL_ID", "gemini-3.5-flash")
            }
        }
    }

    # 1. Individual environment variables
    gemini_key = os.getenv("GEMINI_API_KEY")
    maps_key = os.getenv("MAPS_API_KEY")
    youtube_key = os.getenv("YOUTUBE_API_KEY")

    if gemini_key: config["apiKeys"]["gemini"] = gemini_key
    if maps_key: config["apiKeys"]["maps"] = maps_key
    if youtube_key: config["apiKeys"]["youtube"] = youtube_key

    # 2. AGENT_CONFIG_JSON env var
    config_json_env = os.getenv("AGENT_CONFIG_JSON")
    if config_json_env:
        try:
            env_config = json.loads(config_json_env)
            # Merge env_config into config
            if "apiKeys" in env_config:
                config["apiKeys"].update(env_config["apiKeys"])
            if "models" in env_config:
                config["models"].update(env_config["models"])
        except Exception as e:
            logger.warning(f"Failed to parse AGENT_CONFIG_JSON: {e}")

    # 3. config.json file
    # Check current dir and parent dir
    possible_paths = [
        "config.json",
        os.path.join(os.path.dirname(__file__), "config.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    file_config = json.load(f)
                    # Merge file_config into config (but don't override env vars)
                    if "apiKeys" in file_config:
                        for k, v in file_config["apiKeys"].items():
                            if k not in config["apiKeys"]:
                                config["apiKeys"][k] = v
                    if "models" in file_config:
                        config["models"].update(file_config["models"])
                break # Stop at first found config.json
            except Exception as e:
                logger.warning(f"Failed to parse {path}: {e}")

    return config
