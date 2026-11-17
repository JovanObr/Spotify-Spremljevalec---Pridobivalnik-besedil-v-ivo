"""Start the web server:  python -m api"""

import os

import uvicorn

from core.config import BASE_DIR
from utils import persistent_cache


def main():
    # Port 8888 matches the Spotify redirect URI (http://127.0.0.1:8888/callback)
    port = int(os.getenv("PORT", "8888"))
    reload = os.getenv("API_RELOAD", "").lower() in ("1", "true", "yes")

    # Keep lyrics and AI answers across restarts (.data/cache.sqlite3)
    persistent_cache.enable_default(BASE_DIR)

    print(f"Spotify Sound Companion running at http://127.0.0.1:{port}")

    uvicorn.run("api.app:app", host="127.0.0.1", port=port, reload=reload)


if __name__ == "__main__":
    main()
