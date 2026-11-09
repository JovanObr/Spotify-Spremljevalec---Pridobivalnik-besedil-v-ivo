"""
Search Spotify for songs, artists, albums and playlists.

Since February 2026 Spotify returns at most 10 results per type, which
suits a focused app: one request gives a compact result list.
"""

import spotipy

from models.playlist import PlaylistSummary
from models.track import Track
from services.library_service import get_current_user_id
from utils.cache import TTLCache


SEARCH_TYPES = ("track", "artist", "album", "playlist")
RESULTS_PER_TYPE = 10  # Spotify's maximum

_cache = TTLCache(ttl_seconds=60, max_size=128)


def _image(images) -> str | None:
    images = images or []
    return images[0].get("url") if images else None


def _album(album: dict) -> dict:
    return {
        "id": album.get("id"),
        "uri": album.get("uri"),
        "name": album.get("name") or "Unknown album",
        "artist": ", ".join(a.get("name", "") for a in album.get("artists") or []) or "Unknown",
        "image_url": _image(album.get("images")),
        "year": (album.get("release_date") or "")[:4] or None,
    }


def _artist(artist: dict) -> dict:
    return {
        "id": artist.get("id"),
        "uri": artist.get("uri"),
        "name": artist.get("name") or "Unknown artist",
        "image_url": _image(artist.get("images")),
    }


def search(spotify: spotipy.Spotify, query: str, types: tuple[str, ...] = SEARCH_TYPES) -> dict:
    """
    Returns {"tracks": [...], "artists": [...], "albums": [...], "playlists": [...]}.
    Results Spotify sends as null (removed items) are skipped.
    """
    query = " ".join(query.split())
    types = tuple(t for t in types if t in SEARCH_TYPES) or SEARCH_TYPES

    if not query:
        return {"tracks": [], "artists": [], "albums": [], "playlists": []}

    def fetch():
        data = spotify.search(
            q=query,
            type=",".join(types),
            limit=RESULTS_PER_TYPE,
            market="from_token",
        ) or {}

        def items(key):
            return [item for item in (data.get(key) or {}).get("items") or [] if item]

        user_id = get_current_user_id(spotify) if "playlist" in types else None

        return {
            "tracks": [
                Track.from_spotify(item).to_dict()
                for item in items("tracks")
                if item.get("uri")
            ],
            "artists": [_artist(item) for item in items("artists") if item.get("uri")],
            "albums": [_album(item) for item in items("albums") if item.get("uri")],
            "playlists": [
                PlaylistSummary.from_spotify(item, user_id).to_dict()
                for item in items("playlists")
                if item.get("id")
            ],
        }

    return _cache.get_or_set((query.casefold(), types), fetch)


def clear_cache() -> None:
    _cache.clear()
