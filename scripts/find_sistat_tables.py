"""
Lists SiStat (Statistical Office of Slovenia) tables about music, concerts
and stage events, with their dimensions, so we can pick the one the
"Music in Slovenia" page uses.

Run from the project root:  python scripts/find_sistat_tables.py
Takes about a minute; it pauses between requests to stay under SiStat's
rate limit (30 requests per 10 seconds).
"""

import re
import sys
import time

import requests

API = "https://pxweb.stat.si/SiStatData/api/v1/en/Data"
KEYWORDS = re.compile(r"music|concert|stage|performance|cultural (event|activit)|festival|orchestra|opera", re.I)
FOLDER_HINT = re.compile(r"cultur", re.I)

session = requests.Session()
session.headers["User-Agent"] = "SpotifySoundCompanion/1.0 (student project)"


def get(path):
    time.sleep(0.4)
    response = session.get(f"{API}/{path}".rstrip("/"), timeout=20)
    response.raise_for_status()
    return response.json()


def walk(path, depth=0):
    for item in get(path):
        item_path = f"{path}/{item['id']}" if path else item["id"]
        if item["type"] == "l":
            if depth > 0 or FOLDER_HINT.search(item["text"]):
                print("  " * depth + f"[{item['text']}]", flush=True)
                walk(item_path, depth + 1)
        elif item["type"] == "t" and KEYWORDS.search(item["text"]):
            print("  " * depth + f"TABLE {item_path}: {item['text']}", flush=True)
            try:
                meta = get(item_path)
                for variable in meta.get("variables", []):
                    values = variable.get("valueTexts", [])
                    sample = ", ".join(values[:6]) + (" ..." if len(values) > 6 else "")
                    print("  " * depth + f"    - {variable['text']} ({len(values)}): {sample}", flush=True)
            except requests.RequestException as error:
                print("  " * depth + f"    (metadata failed: {error})")


if __name__ == "__main__":
    try:
        walk("")
    except requests.RequestException as error:
        sys.exit(f"SiStat request failed: {error}")
