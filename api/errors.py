"""Translate Spotify and AI errors into HTTP errors the frontend understands."""

import logging

from fastapi import HTTPException
from spotipy.exceptions import SpotifyException

from services import ai_service


# uvicorn's logger, so the reason shows up next to the "502" line
logger = logging.getLogger("uvicorn.error")


def ai_http_error(error: ai_service.AIServiceError) -> HTTPException:
    """
    503: no key configured. 429: quota used up. 502: the AI call failed
    (often a temporary overload or an unreadable answer; the frontend
    retries those).
    """
    if isinstance(error, ai_service.AINotConfiguredError):
        return HTTPException(503, str(error))
    status = 429 if error.status_code == 429 else 502
    logger.warning("AI request failed (%s): %s", status, error)
    return HTTPException(status, str(error))


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
