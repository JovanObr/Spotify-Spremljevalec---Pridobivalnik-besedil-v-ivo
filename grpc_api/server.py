"""
gRPC server for Spotify Sound Companion.

The servicer is a thin layer, like the FastAPI routes in api/: every call goes
to the same services (Spotify, lyrics, AI), so both servers behave the same.
"""

import functools
import logging
import threading
import time
from concurrent import futures

import grpc
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from models.track import Playback
from services import ai_service, lyrics_service, search_service, spotify_service
from utils.spotify_errors import get_retry_delay

from grpc_api import companion_pb2 as pb
from grpc_api import companion_pb2_grpc as pb_grpc
from grpc_api.convert import lyrics_message, playback_message, track_from_dict
from grpc_api.tracker import PlaybackTracker


logger = logging.getLogger("grpc_api")

DEFAULT_PORT = 50051
DEFAULT_POLL_MS = 2000
MIN_POLL_MS = 1000
MAX_POLL_MS = 10_000
# How often the stream checks whether a new lyric line has started
TICK_SECONDS = 0.1
# Several streams share one Spotify request per second
PLAYBACK_CACHE_SECONDS = 1.0


class SpotifyConnection:
    """The Spotify client plus a short shared cache of the player state."""

    def __init__(self, client):
        self.client = client
        self._lock = threading.Lock()
        self._cached: Playback | None = None
        self._cached_at = float("-inf")

    def current_playback(self) -> Playback | None:
        with self._lock:
            if time.monotonic() - self._cached_at < PLAYBACK_CACHE_SECONDS:
                return self._cached
        playback = spotify_service.get_current_playback(self.client)
        with self._lock:
            self._cached = playback
            self._cached_at = time.monotonic()
        return playback

    def forget_playback(self) -> None:
        with self._lock:
            self._cached_at = float("-inf")


# ---------------------------------------------------------------------------
# Errors -> gRPC status codes
# ---------------------------------------------------------------------------

def status_for(error: Exception) -> tuple[grpc.StatusCode, str]:
    """The gRPC status code and message for an error from the services."""

    if isinstance(error, SpotifyException):
        status = getattr(error, "http_status", None)
        if status == 401:
            return grpc.StatusCode.UNAUTHENTICATED, "Spotify login expired. Restart the server to log in again."
        if status == 403:
            return grpc.StatusCode.PERMISSION_DENIED, "Spotify refused this (playback control needs Premium)."
        if status == 404:
            return grpc.StatusCode.NOT_FOUND, "No active Spotify device. Start playing in any Spotify app first."
        if status == 429:
            return grpc.StatusCode.RESOURCE_EXHAUSTED, "Spotify rate limit reached. Try again shortly."
        return grpc.StatusCode.UNAVAILABLE, f"Spotify error: {getattr(error, 'msg', error)}"

    if isinstance(error, ai_service.AINotConfiguredError):
        return grpc.StatusCode.FAILED_PRECONDITION, str(error)
    if isinstance(error, ai_service.AIServiceError):
        if error.status_code == 429:
            return grpc.StatusCode.RESOURCE_EXHAUSTED, str(error)
        return grpc.StatusCode.UNAVAILABLE, str(error)
    if isinstance(error, lyrics_service.LyricsRateLimitError):
        return grpc.StatusCode.RESOURCE_EXHAUSTED, str(error)
    if isinstance(error, lyrics_service.LyricsServiceError):
        return grpc.StatusCode.UNAVAILABLE, str(error)
    if isinstance(error, ValueError):
        return grpc.StatusCode.INVALID_ARGUMENT, str(error)
    if isinstance(error, RequestException):
        return grpc.StatusCode.UNAVAILABLE, f"Network error: {error}"

    return grpc.StatusCode.INTERNAL, "Unexpected server error."


EXPECTED_ERRORS = (
    SpotifyException,
    ai_service.AIServiceError,
    lyrics_service.LyricsServiceError,
    ValueError,
    RequestException,
)


def unary(method):
    """Log each call with its duration and turn service errors into statuses."""

    @functools.wraps(method)
    def wrapper(self, request, context):
        started = time.perf_counter()
        try:
            response = method(self, request, context)
        except EXPECTED_ERRORS as error:
            code, message = status_for(error)
            logger.warning("%s -> %s: %s", method.__name__, code.name, message)
            context.abort(code, message)
        except Exception:
            logger.exception("%s failed", method.__name__)
            context.abort(grpc.StatusCode.INTERNAL, "Unexpected server error.")
        logger.info("%s OK in %.0f ms", method.__name__, (time.perf_counter() - started) * 1000)
        return response

    return wrapper


def _require(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must not be empty.")
    return value


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------

ACTIONS = {
    pb.PLAYER_ACTION_PLAY: "play",
    pb.PLAYER_ACTION_PAUSE: "pause",
    pb.PLAYER_ACTION_NEXT: "next",
    pb.PLAYER_ACTION_PREVIOUS: "previous",
}


class SoundCompanionServicer(pb_grpc.SoundCompanionServicer):

    def __init__(self, spotify: SpotifyConnection, sleep=time.sleep, clock=time.monotonic):
        self.spotify = spotify
        self._sleep = sleep
        self._clock = clock

    @unary
    def GetNowPlaying(self, request, context):
        playback = self.spotify.current_playback()
        if playback is None:
            return pb.NowPlayingResponse()
        return pb.NowPlayingResponse(playback=playback_message(playback))

    @unary
    def SearchTracks(self, request, context):
        query = _require(request.query, "Query")
        limit = request.limit if 0 < request.limit <= 10 else 10
        results = search_service.search(self.spotify.client, query, ("track",))
        return pb.SearchResponse(tracks=[track_from_dict(item) for item in results["tracks"][:limit]])

    @unary
    def GetLyrics(self, request, context):
        lyrics = lyrics_service.get_lyrics(
            _require(request.artist, "Artist"),
            _require(request.title, "Title"),
            request.album or None,
            request.duration_ms or None,
        )
        return lyrics_message(lyrics)

    @unary
    def GetSongFacts(self, request, context):
        facts = ai_service.generate_track_facts(
            _require(request.artist, "Artist"),
            _require(request.title, "Title"),
            request.album or None,
            request.language.strip() or ai_service.DEFAULT_LANGUAGE,
        )
        return pb.FactsResponse(facts=facts)

    @unary
    def ControlPlayback(self, request, context):
        client = self.spotify.client

        if request.action == pb.PLAYER_ACTION_PLAY_TRACK:
            uri = _require(request.track_uri, "track_uri")
            if not uri.startswith("spotify:track:"):
                raise ValueError("track_uri must look like spotify:track:...")
            if request.album_uri:
                spotify_service.play_context(client, request.album_uri, uri)
            else:
                spotify_service.play_track(client, uri)
            message = "Playing the chosen song."
        elif request.action in ACTIONS:
            action = ACTIONS[request.action]
            spotify_service.control_playback(client, action)
            message = f"Sent {action}."
        else:
            raise ValueError("Choose an action.")

        self.spotify.forget_playback()  # the next answer should show the change
        return pb.ControlResponse(ok=True, message=message)

    def WatchPlayback(self, request, context):
        """Server streaming: runs until the client cancels or disconnects."""

        poll_ms = request.poll_interval_ms or DEFAULT_POLL_MS
        poll_seconds = min(max(poll_ms, MIN_POLL_MS), MAX_POLL_MS) / 1000
        tracker = PlaybackTracker(self._lookup_lyrics if request.include_lyrics else None)

        logger.info("WatchPlayback started (poll every %.1f s, lyrics=%s)", poll_seconds, request.include_lyrics)
        sent = 0
        next_poll = self._clock()

        try:
            while context.is_active():
                now = self._clock()
                events = []

                if now >= next_poll:
                    try:
                        events += tracker.update(self.spotify.current_playback(), now)
                        next_poll = now + poll_seconds
                    except EXPECTED_ERRORS as error:
                        code, message = status_for(error)
                        if code in (grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.PERMISSION_DENIED):
                            context.abort(code, message)
                        # Temporary: keep the stream open and try again later
                        delay = get_retry_delay(error) if isinstance(error, SpotifyException) else None
                        logger.warning("WatchPlayback: %s (retrying)", message)
                        next_poll = now + max(delay or 0, 5)
                else:
                    events += tracker.tick(now)

                for event in events:
                    event.sent_at_ms = int(time.time() * 1000)
                    sent += 1
                    yield event

                self._sleep(TICK_SECONDS)
        finally:
            logger.info("WatchPlayback ended after %d events", sent)

    @staticmethod
    def _lookup_lyrics(playback: Playback):
        track = playback.track
        try:
            return lyrics_service.get_lyrics(
                track.primary_artist, track.title, track.album, track.duration_ms
            )
        except (lyrics_service.LyricsServiceError, ValueError) as error:
            logger.warning("No lyrics for %s: %s", track.title, error)
            return None


def create_server(spotify: SpotifyConnection, port: int = DEFAULT_PORT, host: str = "127.0.0.1"):
    """A started gRPC server. Returns (server, bound_port)."""

    # Each open WatchPlayback stream keeps one worker busy
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    pb_grpc.add_SoundCompanionServicer_to_server(SoundCompanionServicer(spotify), server)
    bound = server.add_insecure_port(f"{host}:{port}")
    if bound == 0:
        raise RuntimeError(f"Port {port} is already in use.")
    server.start()
    return server, bound
