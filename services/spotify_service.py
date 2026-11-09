import spotipy

from spotipy.oauth2 import SpotifyOAuth

from core.config import SPOTIFY_CACHE_PATH, get_spotify_config
from models.track import REPEAT_MODES, Device, Playback, Track


# Every permission the app needs, including ones for planned features
# (see docs/ROADMAP.md). Changing this list makes users log in again, because
# a saved token that lacks any scope listed here counts as logged out, so
# planned scopes are requested up front to avoid repeated logins.
SPOTIFY_SCOPES = [
    "user-read-currently-playing",
    "user-read-playback-state",     # devices, shuffle/repeat, queue
    "user-modify-playback-state",   # play/pause/skip/seek (Premium only)
    "playlist-read-private",        # the user's own and followed playlists
    "playlist-read-collaborative",
    "user-library-read",            # liked songs
    "user-library-modify",          # like / unlike
    "user-read-recently-played",
    "streaming",                    # Web Playback SDK (play in the browser)
    "user-read-email",              # required by the Web Playback SDK
    "user-read-private",            # required by the Web Playback SDK
]

SPOTIFY_SCOPE = " ".join(SPOTIFY_SCOPES)

PLAYER_ACTIONS = ("play", "pause", "next", "previous")


def create_auth_manager(open_browser: bool = True) -> SpotifyOAuth:
    """
    Create the Spotify OAuth 2.0 (Authorization Code Flow) manager.

    The token cache is stored in the project root, so the CLI and the web
    server share the same login.

    Args:
        open_browser: True for the CLI (Spotipy opens the browser itself).
            The web server uses False and handles /login and /callback.
    """
    client_id, client_secret, redirect_uri = get_spotify_config()

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPE,
        cache_path=str(SPOTIFY_CACHE_PATH),
        open_browser=open_browser,
    )


def create_spotify_client(
    auth_manager: SpotifyOAuth | None = None,
) -> spotipy.Spotify:
    """Create an authenticated Spotify API client."""

    return spotipy.Spotify(
        auth_manager=auth_manager or create_auth_manager(),
        requests_timeout=10,
        retries=0,  # The callers handle retries and rate limits themselves
    )


def get_current_playback(spotify: spotipy.Spotify) -> Playback | None:
    """
    The current music track with full player state (device, shuffle,
    repeat, volume), or None when nothing is playing.
    """
    return Playback.from_spotify(spotify.current_playback())


def control_playback(spotify: spotipy.Spotify, action: str) -> None:
    """
    Control playback on the user's active Spotify device.

    Spotify only allows this for Premium accounts.

    Raises:
        ValueError: Unknown action.
        SpotifyException: The Spotify API rejected the request.
    """
    commands = {
        "play": spotify.start_playback,
        "pause": spotify.pause_playback,
        "next": spotify.next_track,
        "previous": spotify.previous_track,
    }

    if action not in commands:
        raise ValueError(f"Unknown player action: {action}")

    commands[action]()


def seek(spotify: spotipy.Spotify, position_ms: int) -> None:
    """Jump to a position (milliseconds) in the current track."""

    if position_ms < 0:
        raise ValueError("Position must not be negative.")

    spotify.seek_track(position_ms)


def play_context(
    spotify: spotipy.Spotify,
    context_uri: str,
    offset_uri: str | None = None,
    device_id: str | None = None,
) -> None:
    """Start a playlist or album, optionally from a specific track."""

    spotify.start_playback(
        device_id=device_id,
        context_uri=context_uri,
        offset={"uri": offset_uri} if offset_uri else None,
    )


def play_track(
    spotify: spotipy.Spotify, track_uri: str, device_id: str | None = None
) -> None:
    """Play a single song now."""

    spotify.start_playback(device_id=device_id, uris=[track_uri])


def add_to_queue(spotify: spotipy.Spotify, track_uri: str) -> None:
    """Add a song to the end of the user's queue."""

    spotify.add_to_queue(track_uri)


MAX_TRACK_URIS = 100


def play_tracks(
    spotify: spotipy.Spotify,
    track_uris: list[str],
    offset_uri: str | None = None,
    device_id: str | None = None,
) -> None:
    """Play a list of songs (e.g. liked songs), optionally starting at one."""

    spotify.start_playback(
        device_id=device_id,
        uris=track_uris[:MAX_TRACK_URIS],
        offset={"uri": offset_uri} if offset_uri else None,
    )


def get_devices(spotify: spotipy.Spotify) -> list[Device]:
    """Spotify apps and speakers the user can play on right now."""

    return [
        Device.from_spotify(device)
        for device in (spotify.devices() or {}).get("devices") or []
    ]


def transfer_playback(spotify: spotipy.Spotify, device_id: str, play: bool = True) -> None:
    """Move playback to another device."""

    spotify.transfer_playback(device_id, force_play=play)


def set_shuffle(spotify: spotipy.Spotify, state: bool, device_id: str | None = None) -> None:
    spotify.shuffle(state, device_id=device_id)


def set_repeat(spotify: spotipy.Spotify, mode: str, device_id: str | None = None) -> None:
    if mode not in REPEAT_MODES:
        raise ValueError(f"Repeat mode must be one of {REPEAT_MODES}.")
    spotify.repeat(mode, device_id=device_id)


def set_volume(spotify: spotipy.Spotify, percent: int, device_id: str | None = None) -> None:
    if not 0 <= percent <= 100:
        raise ValueError("Volume must be between 0 and 100.")
    spotify.volume(percent, device_id=device_id)


QUEUE_LIMIT = 20


def get_queue(spotify: spotipy.Spotify) -> dict:
    """
    What's playing and what comes next (music tracks only, at most 20).

    Spotify's queue endpoint pads the list: when a single song plays without
    an album/playlist, or a short playlist wraps around, it repeats the same
    songs (even with repeat off). Each song is therefore listed once, and
    the current song isn't listed again.

    Returns {"current": Track | None, "next": [Track, ...]}.
    """
    data = spotify.queue() or {}

    def to_track(item):
        if isinstance(item, dict) and item.get("type", "track") == "track":
            return Track.from_spotify(item)
        return None

    current = to_track(data.get("currently_playing"))
    seen = {current.uri} if current and current.uri else set()

    upcoming = []
    for track in map(to_track, data.get("queue") or []):
        if track is None or (track.uri and track.uri in seen):
            continue
        if track.uri:
            seen.add(track.uri)
        upcoming.append(track)

    return {"current": current, "next": upcoming[:QUEUE_LIMIT]}
