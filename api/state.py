"""
Shared Spotify state for the web API.

Routes receive it through FastAPI's dependency injection
(`Depends(get_spotify_state)`), so tests can swap it for a fake with
`app.dependency_overrides`.
"""

import threading
import time

from fastapi import HTTPException

from services.prefetch_service import prefetcher
from services.spotify_service import (
    create_auth_manager,
    create_spotify_client,
    get_current_playback,
)


# Several browser tabs polling at once share one Spotify request.
NOW_PLAYING_CACHE_SECONDS = 1.0


class SpotifyState:
    def __init__(self):
        self._lock = threading.Lock()
        self._auth_manager = None
        self._client = None
        self._cached_playback = None
        self._cached_at = 0.0

    @property
    def auth_manager(self):
        with self._lock:
            if self._auth_manager is None:
                try:
                    self._auth_manager = create_auth_manager(
                        open_browser=False
                    )
                except RuntimeError as error:  # missing .env values
                    raise HTTPException(500, str(error)) from error
            return self._auth_manager

    @property
    def client(self):
        auth_manager = self.auth_manager
        with self._lock:
            if self._client is None:
                self._client = create_spotify_client(auth_manager)
            return self._client

    def is_authenticated(self) -> bool:
        token = self.auth_manager.validate_token(
            self.auth_manager.cache_handler.get_cached_token()
        )
        return token is not None

    def current_playback(self):
        now = time.monotonic()

        with self._lock:
            if now - self._cached_at < NOW_PLAYING_CACHE_SECONDS:
                return self._cached_playback

        playback = get_current_playback(self.client)

        with self._lock:
            self._cached_playback = playback
            self._cached_at = time.monotonic()

        # New song: start preparing its lyrics/facts and the next song's
        prefetcher.on_playback(self.client, playback)

        return playback

    def forget_playback(self):
        with self._lock:
            self._cached_at = 0.0


_spotify_state = SpotifyState()


def get_spotify_state() -> SpotifyState:
    return _spotify_state


def require_login(state: SpotifyState) -> None:
    if not state.is_authenticated():
        raise HTTPException(401, "Not logged in to Spotify.")
