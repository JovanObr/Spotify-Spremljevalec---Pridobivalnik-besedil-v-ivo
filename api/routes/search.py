"""Search Spotify."""

from fastapi import APIRouter, Depends, HTTPException, Query
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from api.errors import spotify_http_error
from api.state import SpotifyState, get_spotify_state, require_login
from services import search_service


router = APIRouter(prefix="/api")


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=200),
    type: str = Query(default="track,artist,album,playlist"),
    state: SpotifyState = Depends(get_spotify_state),
):
    """Songs, artists, albums and playlists matching q (at most 10 of each)."""

    require_login(state)
    types = tuple(t.strip() for t in type.split(",") if t.strip())

    try:
        return search_service.search(state.client, q, types)
    except SpotifyException as error:
        raise spotify_http_error(error) from error
    except RequestException as error:
        raise HTTPException(503, f"Network error: {error}") from error
