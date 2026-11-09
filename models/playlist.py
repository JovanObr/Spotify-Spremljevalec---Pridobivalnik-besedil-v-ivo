"""
Normalized playlist models.

Since February 2026 Spotify names a playlist's tracks "items" (previously
"tracks"), and each entry's track "item" (previously "track"). The helpers
below accept both, so the app keeps working with either response shape.
"""

import html
import re

from dataclasses import asdict, dataclass

from models.track import Track


_TAGS = re.compile(r"<[^>]+>")


def _clean_description(text: str | None) -> str | None:
    """Spotify descriptions can contain HTML links and entities."""
    if not text:
        return None
    cleaned = html.unescape(_TAGS.sub("", text)).strip()
    return cleaned or None


def _contents(playlist: dict) -> dict | None:
    """The playlist's item collection ("items", formerly "tracks")."""
    contents = playlist.get("items")
    if not isinstance(contents, dict):
        contents = playlist.get("tracks")
    return contents if isinstance(contents, dict) else None


def _image(playlist: dict) -> str | None:
    images = playlist.get("images") or []
    return images[0].get("url") if images else None


@dataclass(frozen=True)
class PlaylistSummary:
    id: str
    uri: str
    name: str
    description: str | None
    image_url: str | None
    owner_name: str
    is_owned: bool
    track_count: int | None

    @classmethod
    def from_spotify(cls, playlist: dict, user_id: str | None) -> "PlaylistSummary":
        owner = playlist.get("owner") or {}
        contents = _contents(playlist) or {}

        return cls(
            id=playlist["id"],
            uri=playlist.get("uri") or f"spotify:playlist:{playlist['id']}",
            name=playlist.get("name") or "Untitled playlist",
            description=_clean_description(playlist.get("description")),
            image_url=_image(playlist),
            owner_name=owner.get("display_name") or owner.get("id") or "Unknown",
            # Spotify shares track lists only for playlists the user owns or
            # collaborates on
            is_owned=bool(
                (user_id and owner.get("id") == user_id)
                or playlist.get("collaborative")
            ),
            track_count=contents.get("total"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlaylistDetail(PlaylistSummary):
    snapshot_id: str | None
    # False when Spotify withholds the track list (playlists you don't own)
    items_available: bool

    @classmethod
    def from_spotify(cls, playlist: dict, user_id: str | None) -> "PlaylistDetail":
        summary = PlaylistSummary.from_spotify(playlist, user_id)
        contents = _contents(playlist)

        return cls(
            **asdict(summary),
            snapshot_id=playlist.get("snapshot_id"),
            items_available=bool(
                contents is not None and "items" in contents
                or summary.is_owned
            ),
        )


@dataclass(frozen=True)
class PlaylistItem:
    position: int
    added_at: str | None
    track: Track

    @classmethod
    def from_spotify(cls, entry: dict, position: int) -> "PlaylistItem | None":
        """
        Build an item from a playlist entry. Returns None for entries that
        aren't music tracks (podcast episodes, removed tracks).
        """
        item = entry.get("item")
        if not isinstance(item, dict):
            item = entry.get("track")

        if not isinstance(item, dict) or item.get("type", "track") != "track":
            return None

        if entry.get("is_local") and "is_local" not in item:
            item = {**item, "is_local": True}

        return cls(
            position=position,
            added_at=entry.get("added_at"),
            track=Track.from_spotify(item),
        )

    def to_dict(self) -> dict:
        return {
            "position": self.position,
            "added_at": self.added_at,
            "track": self.track.to_dict(),
        }
