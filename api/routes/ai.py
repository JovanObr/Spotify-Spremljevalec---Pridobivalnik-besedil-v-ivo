"""AI features powered by Google Gemini."""

from fastapi import APIRouter, Depends, HTTPException, Query
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from api.errors import spotify_http_error
from api.state import SpotifyState, get_spotify_state, require_login
from services import ai_service, recommendation_service


router = APIRouter(prefix="/api")


@router.get("/facts")
def facts(
    artist: str = Query(min_length=1),
    title: str = Query(min_length=1),
    album: str | None = None,
    language: str = Query(default=ai_service.DEFAULT_LANGUAGE, max_length=40),
):
    try:
        items = ai_service.generate_track_facts(
            artist, title, album, language
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except ai_service.AIServiceError as error:
        raise _ai_http_error(error) from error

    return {"facts": items}


def _ai_http_error(error: ai_service.AIServiceError) -> HTTPException:
    if isinstance(error, ai_service.AINotConfiguredError):
        return HTTPException(503, str(error))
    return HTTPException(429 if error.status_code == 429 else 502, str(error))


@router.get("/recommendations")
def recommendations(
    artist: str = Query(min_length=1),
    title: str = Query(min_length=1),
    album: str | None = None,
    track_uri: str | None = Query(default=None, pattern=r"^spotify:track:[A-Za-z0-9]+$"),
    state: SpotifyState = Depends(get_spotify_state),
):
    """Up to three songs you might like if you like this one (AI + Spotify search)."""

    require_login(state)

    try:
        items = recommendation_service.get_recommendations(
            state.client, artist, title, album, track_uri
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except ai_service.AIServiceError as error:
        raise _ai_http_error(error) from error
    except SpotifyException as error:
        raise spotify_http_error(error) from error
    except RequestException as error:
        raise HTTPException(503, f"Network error: {error}") from error

    return {"items": [item.to_dict() for item in items]}
