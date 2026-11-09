import os
from pathlib import Path

from dotenv import load_dotenv


# Project root, so paths work no matter which directory the app is started from.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from the project's .env file
load_dotenv(BASE_DIR / ".env")


SPOTIFY_CACHE_PATH = BASE_DIR / ".cache"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
# Legacy: GEMINI_MODEL is no longer used by any feature (see the two below)
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
# Facts are shown while a song plays, so they use Google's low-latency model
DEFAULT_GEMINI_FACTS_MODEL = "gemini-3.5-flash-lite"
# Recommendations: Gemma 4 has a much larger free daily quota than Gemini Flash
DEFAULT_GEMINI_RECOMMENDATIONS_MODEL = "gemma-4-31b-it"
DEFAULT_LYRICS_PROVIDERS = ("lrclib", "lyricsovh")


def get_required_env(name: str) -> str:
    """
    Retrieve a required environment variable.

    Raises:
        RuntimeError: If the variable is missing or empty.
    """
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def get_spotify_config() -> tuple[str, str, str]:
    """
    Retrieve the Spotify configuration.

    Raises:
        RuntimeError: If a required Spotify variable is missing.
    """
    client_id = get_required_env("SPOTIPY_CLIENT_ID")
    client_secret = get_required_env("SPOTIPY_CLIENT_SECRET")

    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI") or DEFAULT_REDIRECT_URI

    return client_id, client_secret, redirect_uri


def get_gemini_config() -> tuple[str, str]:
    """
    Retrieve the Google Gemini (AI Studio) configuration.

    Raises:
        RuntimeError: If GEMINI_API_KEY is missing.
    """
    api_key = get_required_env("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL

    return api_key, model


def get_gemini_facts_model() -> str:
    """Model for song facts (fast)."""
    return os.getenv("GEMINI_FACTS_MODEL") or DEFAULT_GEMINI_FACTS_MODEL


def get_gemini_recommendations_model() -> str:
    """Model for "If you like this" recommendations (Gemini or Gemma)."""
    return (
        os.getenv("GEMINI_RECOMMENDATIONS_MODEL")
        or DEFAULT_GEMINI_RECOMMENDATIONS_MODEL
    )


def get_lyrics_providers() -> tuple[str, ...]:
    """
    Lyrics sources to try, in order (LYRICS_PROVIDERS="lrclib,lyricsovh").
    Unknown names are ignored.
    """
    raw = os.getenv("LYRICS_PROVIDERS")
    if not raw:
        return DEFAULT_LYRICS_PROVIDERS
    return tuple(
        name.strip().lower() for name in raw.split(",") if name.strip()
    )


def is_prefetch_enabled() -> bool:
    """Prepare facts and lyrics for the next queued song (PREFETCH_NEXT=0 to disable)."""
    return os.getenv("PREFETCH_NEXT", "1").lower() not in ("0", "false", "no")
