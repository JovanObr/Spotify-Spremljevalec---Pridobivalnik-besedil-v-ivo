"""
The user's Spotify library: playlists, their tracks, and liked songs.

Results are cached briefly so moving between views doesn't call Spotify
again each time. Playlist pages are keyed by the playlist's snapshot_id,
which changes whenever the playlist is edited, so edits show up right away.
"""

import spotipy

from models.playlist import PlaylistDetail, PlaylistItem, PlaylistSummary
from utils.cache import TTLCache


PAGE_SIZE = 50                 # Spotify's maximum for these endpoints
MAX_PLAYLISTS = 1000           # Safety limit when collecting all pages

_user_cache = TTLCache(ttl_seconds=3600, max_size=4)
_playlists_cache = TTLCache(ttl_seconds=60, max_size=4)
_detail_cache = TTLCache(ttl_seconds=60, max_size=128)
_items_cache = TTLCache(ttl_seconds=600, max_size=512)
_liked_cache = TTLCache(ttl_seconds=30, max_size=64)


def get_current_user_id(spotify: spotipy.Spotify) -> str | None:
    return _user_cache.get_or_set("me", lambda: (spotify.me() or {}).get("id"))


def list_playlists(spotify: spotipy.Spotify) -> list[PlaylistSummary]:
    """All playlists in the user's library, in Spotify's order."""

    def fetch():
        user_id = get_current_user_id(spotify)
        playlists: list[PlaylistSummary] = []
        offset = 0

        while offset < MAX_PLAYLISTS:
            page = spotify.current_user_playlists(limit=PAGE_SIZE, offset=offset)
            entries = page.get("items") or []

            playlists.extend(
                PlaylistSummary.from_spotify(entry, user_id)
                for entry in entries
                if entry and entry.get("id")
            )

            if not page.get("next") or not entries:
                break
            offset += len(entries)

        return playlists

    return _playlists_cache.get_or_set("all", fetch)


def get_playlist(spotify: spotipy.Spotify, playlist_id: str) -> PlaylistDetail:
    def fetch():
        user_id = get_current_user_id(spotify)
        return PlaylistDetail.from_spotify(spotify.playlist(playlist_id), user_id)

    return _detail_cache.get_or_set(playlist_id, fetch)


def get_playlist_items(
    spotify: spotipy.Spotify,
    playlist_id: str,
    offset: int = 0,
    limit: int = PAGE_SIZE,
) -> dict:
    """
    One page of a playlist's tracks.

    Returns {"items": [...], "total": int, "next_offset": int | None}.
    Podcast episodes and removed tracks are skipped.
    """
    limit = max(1, min(limit, PAGE_SIZE))
    snapshot = get_playlist(spotify, playlist_id).snapshot_id

    def fetch():
        page = spotify.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            additional_types=("track",),
        )
        entries = page.get("items") or []
        items = [
            item
            for index, entry in enumerate(entries)
            if entry
            and (item := PlaylistItem.from_spotify(entry, offset + index))
        ]
        total = page.get("total") or 0
        next_offset = offset + len(entries)

        return {
            "items": items,
            "total": total,
            "next_offset": next_offset if entries and next_offset < total else None,
        }

    return _items_cache.get_or_set((playlist_id, snapshot, offset, limit), fetch)


# ---------------------------------------------------------------------------
# Liked songs
# ---------------------------------------------------------------------------

def get_liked_tracks(spotify: spotipy.Spotify, offset: int = 0, limit: int = PAGE_SIZE) -> dict:
    """
    One page of the user's liked songs, newest first.

    Returns {"items": [PlaylistItem, ...], "total": int, "next_offset": int | None}.
    """
    limit = max(1, min(limit, PAGE_SIZE))

    def fetch():
        page = spotify.current_user_saved_tracks(limit=limit, offset=offset)
        entries = page.get("items") or []
        items = [
            item
            for index, entry in enumerate(entries)
            if entry and (item := PlaylistItem.from_spotify(entry, offset + index))
        ]
        total = page.get("total") or 0
        next_offset = offset + len(entries)

        return {
            "items": items,
            "total": total,
            "next_offset": next_offset if entries and next_offset < total else None,
        }

    return _liked_cache.get_or_set((offset, limit), fetch)


MAX_CONTAINS = 40  # Keep each "is it liked?" request small


def are_liked(spotify: spotipy.Spotify, uris: list[str]) -> dict[str, bool]:
    """Whether each track URI is in the user's liked songs."""

    result: dict[str, bool] = {}
    for start in range(0, len(uris), MAX_CONTAINS):
        chunk = uris[start:start + MAX_CONTAINS]
        flags = spotify.current_user_saved_tracks_contains(chunk) or []
        result.update(zip(chunk, (bool(flag) for flag in flags)))
    return result


def set_liked(spotify: spotipy.Spotify, uris: list[str], liked: bool) -> None:
    """Like or unlike songs (Spotify's /me/library endpoints)."""

    if liked:
        spotify.current_user_saved_tracks_add(uris)
    else:
        spotify.current_user_saved_tracks_delete(uris)

    # The liked list changed
    _liked_cache.clear()


def clear_cache() -> None:
    """Forget everything (on logout, so another account starts fresh)."""
    for cache in (_user_cache, _playlists_cache, _detail_cache, _items_cache, _liked_cache):
        cache.clear()
