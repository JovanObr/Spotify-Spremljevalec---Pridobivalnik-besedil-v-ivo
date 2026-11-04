
import spotipy

from spotipy.oauth2 import SpotifyOAuth

from core.config import (
    SPOTIPY_CLIENT_ID,
    SPOTIPY_CLIENT_SECRET,
    SPOTIPY_REDIRECT_URI
)


SPOTIFY_SCOPE = "user-read-currently-playing"


def create_spotify_client() -> spotipy.Spotify:
    """
    Create an authenticated Spotify API client.

    Uses OAuth 2.0 Authorization Code Flow.
    """

    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_path=".cache"
    )

    spotify = spotipy.Spotify(
        auth_manager=auth_manager
    )

    return spotify
