"""
The Data sources page: every outside source, how it's reached, how fresh
its data is, and a way to fetch it again now.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.state import SpotifyState, get_spotify_state
from services import (
    country_service,
    library_service,
    lyrics_service,
    source_registry,
    stats_service,
    wikipedia_service,
)
from utils import persistent_cache


router = APIRouter(prefix="/api")

# How the data reaches the two clients (not outside sources, but part of the picture)
DELIVERY = [
    {
        "id": "rest",
        "name": "This web app",
        "technology": "REST",
        "description": "The browser gets everything from the Python server's REST API (FastAPI, JSON).",
    },
    {
        "id": "grpc",
        "name": "Terminal app",
        "technology": "gRPC",
        "description": "python main.py gets now playing, search, lyrics and facts from the gRPC server "
                       "(python -m grpc_api), including a live stream of lyric lines.",
    },
]


@router.get("/sources")
def sources():
    return {"sources": source_registry.describe(), "delivery": DELIVERY}


def _forget_lyrics():
    lyrics_service.clear_cache()
    persistent_cache.store().clear("lyrics")


REFRESHERS = {
    "lrclib": lambda: _forget_lyrics(),
    "lyrics_ovh": lambda: _forget_lyrics(),
    "wikipedia": lambda: wikipedia_service.clear_cache(),
    "countryinfo": lambda: country_service.clear_cache(),
    "sistat": lambda: stats_service.clear_cache(),
}


@router.post("/sources/{source_id}/refresh")
def refresh(source_id: str, state: SpotifyState = Depends(get_spotify_state)):
    """
    Forget this source's saved data, so the next request fetches it again.
    Not offered for the AI and MusicAtlas, whose requests use a daily quota.
    """
    source = source_registry.BY_ID.get(source_id)
    if source is None:
        raise HTTPException(404, "Unknown source.")
    if not source.refreshable:
        raise HTTPException(409, f"{source.name} isn't refreshed by hand: each request uses its daily quota.")

    if source_id == "spotify":
        library_service.clear_cache()
        state.forget_playback()
    else:
        REFRESHERS[source_id]()

    return {"refreshed": source_id}
