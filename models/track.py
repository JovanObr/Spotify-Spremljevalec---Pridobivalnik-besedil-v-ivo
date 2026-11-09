"""
Normalized track and playback models.

Spotify returns large, deeply nested JSON. These dataclasses pull out only the
fields the app uses, in one place, so the CLI, the web API and the services
all work with the same shape.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Track:
    id: str | None
    title: str
    artists: list[str]
    album: str
    duration_ms: int | None
    artwork_url: str | None
    spotify_url: str | None
    uri: str | None = None
    # Smallest cover image, for lists (falls back to the large one)
    thumbnail_url: str | None = None
    is_local: bool = False
    is_playable: bool = True
    # The song's album, so a single song can be played "in its album" and
    # Spotify has something to continue with afterwards
    album_uri: str | None = None

    @property
    def artist(self) -> str:
        """All artists joined into one display string."""
        return ", ".join(self.artists) or "Unknown"

    @property
    def primary_artist(self) -> str:
        """First listed artist; works best for lyrics and fact lookups."""
        return self.artists[0] if self.artists else "Unknown"

    @classmethod
    def from_spotify(cls, item: dict) -> "Track":
        album = item.get("album") or {}
        images = album.get("images") or []

        return cls(
            id=item.get("id"),
            title=item.get("name") or "Unknown",
            artists=[
                artist["name"]
                for artist in item.get("artists") or []
                if artist.get("name")
            ],
            album=album.get("name") or "Unknown",
            duration_ms=item.get("duration_ms"),
            # Spotify orders images largest first
            artwork_url=images[0].get("url") if images else None,
            spotify_url=(item.get("external_urls") or {}).get("spotify"),
            uri=item.get("uri"),
            thumbnail_url=images[-1].get("url") if images else None,
            is_local=bool(item.get("is_local", False)),
            # Local files can't be started through the Web API
            is_playable=(
                item.get("is_playable", True) is not False
                and not item.get("is_local", False)
            ),
            album_uri=album.get("uri"),
        )

    def to_dict(self) -> dict:
        return {**asdict(self), "artist": self.artist}


@dataclass(frozen=True)
class Device:
    id: str | None
    name: str
    type: str                 # "Computer", "Smartphone", "Speaker", ...
    is_active: bool
    volume_percent: int | None
    supports_volume: bool

    @classmethod
    def from_spotify(cls, device: dict) -> "Device":
        return cls(
            id=device.get("id"),
            name=device.get("name") or "Unknown device",
            type=device.get("type") or "Unknown",
            is_active=bool(device.get("is_active")),
            volume_percent=device.get("volume_percent"),
            supports_volume=bool(device.get("supports_volume", True)),
        )

    def to_dict(self) -> dict:
        return asdict(self)


REPEAT_MODES = ("off", "context", "track")


@dataclass(frozen=True)
class Playback:
    track: Track
    is_playing: bool
    progress_ms: int | None
    # What the track is playing from, e.g. "spotify:playlist:..."
    context_uri: str | None = None
    # Only in full player state responses (GET /me/player)
    shuffle: bool = False
    repeat: str = "off"
    device: Device | None = None

    @classmethod
    def from_spotify(cls, playback: dict | None) -> "Playback | None":
        """
        Build a Playback from a Spotify player response (GET /me/player, or
        the smaller "currently playing" one, which lacks device/shuffle/repeat).

        Returns None when nothing is playing or the item is not a music
        track (e.g. a podcast episode or an ad).
        """
        if not playback:
            return None

        item = playback.get("item")

        if not item or item.get("type") != "track":
            return None

        return cls(
            track=Track.from_spotify(item),
            is_playing=bool(playback.get("is_playing", False)),
            progress_ms=playback.get("progress_ms"),
            context_uri=(playback.get("context") or {}).get("uri"),
            shuffle=bool(playback.get("shuffle_state", False)),
            repeat=(
                playback.get("repeat_state")
                if playback.get("repeat_state") in REPEAT_MODES
                else "off"
            ),
            device=(
                Device.from_spotify(playback["device"])
                if isinstance(playback.get("device"), dict)
                else None
            ),
        )

    def to_dict(self) -> dict:
        return {
            "track": self.track.to_dict(),
            "is_playing": self.is_playing,
            "progress_ms": self.progress_ms,
            "context_uri": self.context_uri,
            "shuffle": self.shuffle,
            "repeat": self.repeat,
            "device": self.device.to_dict() if self.device else None,
        }
