"""The user's playlists and liked songs."""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from api.errors import spotify_http_error
from api.state import SpotifyState, get_spotify_state, require_login
from services import library_service


router = APIRouter(prefix="/api/playlists")
liked_router = APIRouter(prefix="/api/library")

TRACK_URI = r"^spotify:track:[A-Za-z0-9]+$"

PlaylistId = Path(pattern=r"^[A-Za-z0-9]{1,64}$")

NOT_SHARED = (
    "Spotify only shares track lists for playlists you own or "
    "collaborate on. You can still play this playlist."
)


def _call(state: SpotifyState, fetch):
    require_login(state)

    try:
        return fetch(state.client)
    except SpotifyException as error:
        if error.http_status == 404:
            raise HTTPException(404, "Playlist not found.") from error
        raise spotify_http_error(error) from error
    except RequestException as error:
        raise HTTPException(503, f"Network error: {error}") from error


@router.get("")
def playlists(state: SpotifyState = Depends(get_spotify_state)):
    """Every playlist in the user's library, in Spotify's order."""

    items = _call(state, library_service.list_playlists)
    return {"items": [playlist.to_dict() for playlist in items]}


@router.get("/{playlist_id}")
def playlist(
    playlist_id: str = PlaylistId,
    state: SpotifyState = Depends(get_spotify_state),
):
    detail = _call(
        state,
        lambda client: library_service.get_playlist(client, playlist_id),
    )
    return detail.to_dict()


@router.get("/{playlist_id}/items")
def playlist_items(
    playlist_id: str = PlaylistId,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=library_service.PAGE_SIZE, ge=1, le=50),
    state: SpotifyState = Depends(get_spotify_state),
):
    detail = _call(
        state,
        lambda client: library_service.get_playlist(client, playlist_id),
    )

    if not detail.items_available:
        raise HTTPException(403, NOT_SHARED)

    try:
        page = _call(
            state,
            lambda client: library_service.get_playlist_items(
                client, playlist_id, offset, limit
            ),
        )
    except HTTPException as error:
        if error.status_code == 403:
            raise HTTPException(403, NOT_SHARED) from error
        raise

    return {
        **page,
        "items": [item.to_dict() for item in page["items"]],
    }


# ---------------------------------------------------------------------------
# Liked songs
# ---------------------------------------------------------------------------

class LikeRequest(BaseModel):
    uris: list[str] = Field(min_length=1, max_length=40)


def _check_track_uris(uris: list[str]) -> list[str]:
    import re

    if not uris or len(uris) > 40 or not all(re.match(TRACK_URI, uri) for uri in uris):
        raise HTTPException(422, "Give 1-40 Spotify track URIs.")
    return uris


@liked_router.get("/tracks")
def liked_tracks(
    offset: int = Query(default=0, ge=0),
    state: SpotifyState = Depends(get_spotify_state),
):
    """The user's liked songs, newest first, 50 at a time."""

    page = _call(state, lambda client: library_service.get_liked_tracks(client, offset))
    return {**page, "items": [item.to_dict() for item in page["items"]]}


@liked_router.get("/contains")
def liked_contains(
    uris: str = Query(description="Comma-separated track URIs"),
    state: SpotifyState = Depends(get_spotify_state),
):
    """Which of these songs are liked: {"spotify:track:…": true, …}."""

    checked = _check_track_uris([uri for uri in uris.split(",") if uri])
    return _call(state, lambda client: library_service.are_liked(client, checked))


@liked_router.put("/tracks")
def like(body: LikeRequest, state: SpotifyState = Depends(get_spotify_state)):
    uris = _check_track_uris(body.uris)
    _call(state, lambda client: library_service.set_liked(client, uris, True))
    return {"liked": True, "uris": uris}


@liked_router.delete("/tracks")
def unlike(body: LikeRequest, state: SpotifyState = Depends(get_spotify_state)):
    uris = _check_track_uris(body.uris)
    _call(state, lambda client: library_service.set_liked(client, uris, False))
    return {"liked": False, "uris": uris}
