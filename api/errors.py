"""Translate Spotify errors into HTTP errors the frontend understands."""

from fastapi import HTTPException
from spotipy.exceptions import SpotifyException


def spotify_http_error(error: SpotifyException) -> HTTPException:
    status = getattr(error, "http_status", None) or 502
    headers = getattr(error, "headers", None) or {}

    if status == 401:
        return HTTPException(401, "Spotify session expired. Log in again.")

    if status == 403:
        return HTTPException(
            403,
            "Spotify denied access. Check that your account is added "
            "under User Management in the Spotify developer dashboard.",
        )

    if status == 429:
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        return HTTPException(
            429,
            "Spotify rate limit reached.",
            headers={"Retry-After": str(retry_after or 30)},
        )

    return HTTPException(502, f"Spotify API error: {error.msg}")


def player_http_error(error: SpotifyException) -> HTTPException:
    """Errors from play/pause/skip/seek, which have their own common causes."""

    reason = getattr(error, "reason", None)

    if error.http_status == 404 or reason == "NO_ACTIVE_DEVICE":
        return HTTPException(
            409,
            "No active Spotify device. Start playing in a Spotify app first.",
        )

    if reason == "PREMIUM_REQUIRED":
        return HTTPException(403, "Playback controls need Spotify Premium.")

    if error.http_status == 403:
        # e.g. pausing something that is already paused
        return HTTPException(409, "Spotify didn't allow that right now.")

    return spotify_http_error(error)
