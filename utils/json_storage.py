import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"

GROUPS_FILE = STORAGE_DIR / "groups.json"
CONFIG_FILE = STORAGE_DIR / "config.json"
SIGNATURES_FILE = STORAGE_DIR / "channel_signature.json"
MONITORING_GROUPS_PATH = STORAGE_DIR / "monitoring_groups.json"
MEDIA_FILE = STORAGE_DIR / "media.json"

# Ensure storage directory and files exist
if not STORAGE_DIR.exists():
    STORAGE_DIR.mkdir()

for path, default in [
    (GROUPS_FILE, {}),
    (CONFIG_FILE, {"signature": ""}),
    (SIGNATURES_FILE, {}),
    (MEDIA_FILE, {}),
]:
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)

# === UNIVERSAL MEDIA STORAGE ===

def load_known_media() -> dict:
    if MEDIA_FILE.exists():
        with open(MEDIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_known_media(data: dict) -> None:
    with open(MEDIA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def filter_media_by_platform(media: dict, platform: str) -> dict:
    return {k: v for k, v in media.items() if v.get("platform") == platform}

# === GROUPS ===

def load_groups() -> dict:
    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
    except json.JSONDecodeError:
        data = {}
    return data

def save_groups(data: dict) -> None:
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_group(name: str, channels: list[dict]) -> None:
    data = load_groups()
    data[name] = channels
    save_groups(data)

def remove_group(name: str) -> None:
    data = load_groups()
    if name in data:
        data.pop(name)
        save_groups(data)

# === CONFIG (GLOBAL SIGNATURE) ===

def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {"signature": ""}
    except json.JSONDecodeError:
        data = {"signature": ""}
    return data

def save_config(data: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def set_signature(text: str) -> None:
    config = load_config()
    config["signature"] = text
    save_config(config)

def get_signature() -> str:
    config = load_config()
    return config.get("signature", "")

# === PER-CHANNEL SIGNATURES (only for Telegram) ===

def load_channel_signature(channel_id: int | str) -> dict:
    if SIGNATURES_FILE.exists():
        with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(channel_id), {})
    return {}

def save_channel_signature(channel_id: int | str, signature: str, enabled: bool = True) -> None:
    if SIGNATURES_FILE.exists():
        with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data[str(channel_id)] = {"signature": signature, "enabled": enabled}
    with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def delete_channel_signature(channel_id: int | str) -> None:
    if not SIGNATURES_FILE.exists():
        return
    with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop(str(channel_id), None)
    with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# === MONITORING GROUPS ===

def load_monitoring_groups() -> dict:
    try:
        with open(MONITORING_GROUPS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_monitoring_groups(data: dict):
    with open(MONITORING_GROUPS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === TRIM SETTINGS ===

def get_trim_settings(category: str, channel_id: int) -> dict:
    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])
    for ch in channels:
        if ch.get("id") == channel_id:
            settings = {
                "lines_to_trim": ch.get("lines_to_trim", 0),
                "trim_phrases": ch.get("trim_phrases", [])
            }
            logging.debug(f"[get_trim_settings] ✅ Found settings for channel {channel_id}: {settings}")
            return settings
    logging.debug(f"[get_trim_settings] ⛔️ No settings found for channel {channel_id}")
    return {"lines_to_trim": 0, "trim_phrases": []}

def update_trim_settings(category: str, channel_id: int, lines_to_trim: int = None, trim_phrases: list = None):
    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])
    for ch in channels:
        if ch.get("id") == channel_id:
            if lines_to_trim is not None:
                ch["lines_to_trim"] = lines_to_trim
            if trim_phrases is not None and isinstance(trim_phrases, list):
                ch["trim_phrases"] = trim_phrases
            save_monitoring_groups(groups)
            logging.debug(f"[update_trim_settings] 💾 Updated settings for channel {channel_id}")
            return
    logging.warning(f"[update_trim_settings] ⚠️ Channel {channel_id} not found in category '{category}'")
