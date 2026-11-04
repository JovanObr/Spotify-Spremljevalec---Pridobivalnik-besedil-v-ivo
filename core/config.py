
import os

from dotenv import load_dotenv


# Load variables from the .env file
load_dotenv()


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


# Spotify configuration
SPOTIPY_CLIENT_ID = get_required_env("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = get_required_env("SPOTIPY_CLIENT_SECRET")

SPOTIPY_REDIRECT_URI = os.getenv(
    "SPOTIPY_REDIRECT_URI",
    "http://127.0.0.1:8888/callback"
)


# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)
