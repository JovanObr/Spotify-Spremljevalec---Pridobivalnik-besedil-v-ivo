"""
Prepare lyrics and AI facts before they're needed.

When a new song starts, its lyrics, facts and recommendations are
requested in the background right away, and so are those of the next song
in the user's Spotify queue. By the time that song starts, they're usually
cached, so the page shows them instantly instead of waiting for Gemini.

Costs: two extra AI requests (facts + recommendations) per queued song
that gets skipped before it plays.
Disable with PREFETCH_NEXT=0 in .env.
"""

import logging
import threading

from concurrent.futures import Executor, ThreadPoolExecutor

import spotipy

from core.config import is_prefetch_enabled
from models.track import Playback, Track
from services import ai_service, lyrics_service, recommendation_service


log = logging.getLogger(__name__)


def next_in_queue(spotify: spotipy.Spotify) -> Track | None:
    """The next music track in the user's queue, if Spotify tells us."""

    try:
        queue = spotify.queue() or {}
    except Exception as error:  # missing scope, no device, network ...
        log.debug("Could not read the Spotify queue: %s", error)
        return None

    for item in queue.get("queue") or []:
        if isinstance(item, dict) and item.get("type", "track") == "track":
            return Track.from_spotify(item)

    return None


def _lookup_args(track: Track) -> tuple[str, str, str | None]:
    """The same artist/title/album the frontend sends, so caches match."""
    artist = track.artists[0] if track.artists else track.artist
    album = track.album or None
    return artist, track.title, album


class Prefetcher:
    def __init__(self, executor: Executor | None = None):
        self._executor = executor or ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="prefetch"
        )
        self._lock = threading.Lock()
        self._last_track: str | None = None

    def on_playback(self, spotify: spotipy.Spotify, playback: Playback | None):
        """Call with every now-playing result; acts only when the song changes."""

        if playback is None or not is_prefetch_enabled():
            return

        key = playback.track.uri or f"{playback.track.artist}|{playback.track.title}"

        with self._lock:
            if key == self._last_track:
                return
            self._last_track = key

        self._executor.submit(self._prepare, spotify, playback.track)

    def reset(self):
        with self._lock:
            self._last_track = None

    def _prepare(self, spotify: spotipy.Spotify, current: Track):
        self.warm(current, spotify)

        upcoming = next_in_queue(spotify)
        if upcoming and upcoming.uri != current.uri:
            self.warm(upcoming, spotify)

    def warm(self, track: Track, spotify: spotipy.Spotify | None = None):
        """Fill the lyrics, facts and recommendation caches (errors are ignored)."""
        self._executor.submit(self._safely, self._warm_lyrics, track)
        if ai_service.is_configured():
            self._executor.submit(self._safely, self._warm_facts, track)
        if spotify is not None and recommendation_service.is_available():
            self._executor.submit(
                self._safely,
                lambda t: self._warm_recommendations(spotify, t),
                track,
            )

    @staticmethod
    def _warm_lyrics(track: Track):
        artist, title, album = _lookup_args(track)
        lyrics_service.get_lyrics(artist, title, album, track.duration_ms or None)

    @staticmethod
    def _warm_facts(track: Track):
        artist, title, album = _lookup_args(track)
        ai_service.generate_track_facts(artist, title, album)

    @staticmethod
    def _warm_recommendations(spotify: spotipy.Spotify, track: Track):
        artist, title, album = _lookup_args(track)
        recommendation_service.get_recommendations(
            spotify, artist, title, album, track.uri
        )

    @staticmethod
    def _safely(work, track: Track):
        try:
            work(track)
        except Exception as error:
            log.debug("Prefetch for %s failed: %s", track.title, error)


prefetcher = Prefetcher()
