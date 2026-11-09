"""Spotify login (OAuth 2.0 Authorization Code Flow) and app status."""

import os

from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from spotipy.exceptions import SpotifyOauthError

from api.state import SpotifyState, get_spotify_state
from services import ai_service, library_service, search_service
from services.prefetch_service import prefetcher


router = APIRouter()


def safe_next_url(next_url: str | None) -> str:
    """Only allow redirects back to this machine (prevents open redirects)."""

    if not next_url:
        return "/"

    parsed = urlparse(next_url)

    # "/path" is fine; "//host" and "/\host" are treated as other sites
    if (
        not parsed.scheme
        and next_url.startswith("/")
        and next_url[1:2] not in ("/", "\\")
    ):
        return next_url

    if parsed.scheme in ("http", "https") and parsed.hostname in (
        "127.0.0.1",
        "localhost",
    ):
        return next_url

    return "/"


@router.get("/login")
def login(
    next: str | None = None,
    state: SpotifyState = Depends(get_spotify_state),
):
    """Send the user to Spotify's login page."""

    url = state.auth_manager.get_authorize_url(state=safe_next_url(next))
    return RedirectResponse(url)


@router.get("/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    spotify: SpotifyState = Depends(get_spotify_state),
):
    """Spotify redirects here after login (SPOTIPY_REDIRECT_URI)."""

    target = safe_next_url(state)
    separator = "&" if "?" in target else "?"

    if error or not code:
        return RedirectResponse(
            f"{target}{separator}auth_error={error or 'missing_code'}"
        )

    try:
        spotify.auth_manager.get_access_token(
            code, as_dict=False, check_cache=False
        )
    except SpotifyOauthError:
        return RedirectResponse(f"{target}{separator}auth_error=token")

    spotify.forget_playback()
    return RedirectResponse(target)


@router.post("/api/logout")
def logout(state: SpotifyState = Depends(get_spotify_state)):
    cache_path = state.auth_manager.cache_handler.cache_path

    try:
        os.remove(cache_path)
    except FileNotFoundError:
        pass

    state.forget_playback()
    library_service.clear_cache()
    search_service.clear_cache()
    prefetcher.reset()
    return {"authenticated": False}


@router.get("/api/status")
def status(state: SpotifyState = Depends(get_spotify_state)):
    """What is configured and connected. The frontend calls this first."""

    return {
        "authenticated": state.is_authenticated(),
        "ai_enabled": ai_service.is_configured(),
    }
