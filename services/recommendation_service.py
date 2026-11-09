"""
"If you like this song": three songs to play next.

Two sources, tried in order:

1. MusicAtlas (if MUSICATLAS_API_KEY is set): similar songs found by audio
   analysis, with Spotify IDs. Spotify supplies the track details, and the
   AI writes a one-line reason for the picks in a single call (MusicAtlas's
   style tags are shown if that fails).
2. AI fallback (no key, song not in MusicAtlas's catalog, quota reached):
   the AI suggests up to five songs, each is looked up with Spotify search,
   and only songs that really exist on Spotify are kept.

In both cases the current song and duplicates are removed and at most
three are returned.
"""

import logging


from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import spotipy

from models.track import Track
from services import ai_service, musicatlas_service
from services.lyrics_service import clean_title
from utils.cache import TTLCache
from utils.single_flight import SingleFlight
from utils.text import normalize, same_name


MAX_RECOMMENDATIONS = 3
# MusicAtlas candidates to look up on Spotify (some may be unplayable)
MAX_ATLAS_CANDIDATES = 6

log = logging.getLogger(__name__)

_cache = TTLCache(ttl_seconds=6 * 3600, max_size=256)
_in_flight = SingleFlight()
_search_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="rec-search")


@dataclass(frozen=True)
class Recommendation:
    track: Track
    reason: str | None

    def to_dict(self) -> dict:
        return {"track": self.track.to_dict(), "reason": self.reason}


@dataclass(frozen=True)
class RecommendationResult:
    items: list[Recommendation]
    # "musicatlas" or "ai": shown in the UI ("Picked by …")
    source: str
    # Style tags from MusicAtlas, e.g. ["dreampop", "shoegaze"]
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "source": self.source,
            "tags": list(self.tags),
        }


def is_available() -> bool:
    """Whether any recommendation source is configured."""
    return musicatlas_service.is_configured() or ai_service.is_configured()


def _strip_quotes(text: str) -> str:
    return text.replace('"', " ").strip()


def _matches(item: dict, title: str, artist: str) -> bool:
    artists = [a.get("name", "") for a in item.get("artists") or []]
    return (
        same_name(clean_title(item.get("name") or ""), clean_title(title))
        and any(same_name(name, artist) for name in artists)
    )


def find_on_spotify(spotify: spotipy.Spotify, title: str, artist: str) -> Track | None:
    """The Spotify track for a title + artist, or None if it doesn't exist."""

    queries = [
        # Field filters: precise
        f'track:"{_strip_quotes(clean_title(title))}" artist:"{_strip_quotes(artist)}"',
        # Plain text: forgiving about punctuation and featured artists
        f"{_strip_quotes(clean_title(title))} {_strip_quotes(artist)}",
    ]

    for query in queries:
        try:
            result = spotify.search(q=query, type="track", limit=5, market="from_token")
        except spotipy.SpotifyException:
            continue

        items = ((result or {}).get("tracks") or {}).get("items") or []
        for item in items:
            if item and item.get("uri") and _matches(item, title, artist):
                return Track.from_spotify(item)

    return None


def _identity(title: str, artist: str) -> str:
    return f"{normalize(clean_title(title))}|{normalize(artist)}"


def _lookup_spotify_track(spotify: spotipy.Spotify, track_id: str) -> Track | None:
    try:
        item = spotify.track(track_id, market="from_token")
    except spotipy.SpotifyException:
        return None
    if not item or not item.get("uri"):
        return None
    track = Track.from_spotify(item)
    return track if track.is_playable else None


def _from_musicatlas(
    spotify: spotipy.Spotify,
    artist: str,
    title: str,
    track_uri: str | None,
) -> RecommendationResult | None:
    """MusicAtlas picks, or None to fall back to the AI."""

    if not musicatlas_service.is_configured():
        return None

    try:
        similar = musicatlas_service.similar_tracks(artist, title)
    except musicatlas_service.MusicAtlasError as error:
        log.info("MusicAtlas unavailable, using AI recommendations: %s", error)
        return None

    if not similar.in_catalog or not similar.matches:
        return None

    # Candidates: on Spotify, not the current song, one song per artist
    current = _identity(title, artist)
    seen_artists: set[str] = set()
    candidates = []
    for match in similar.matches:
        if not match.spotify_id or _identity(match.title, match.artist) == current:
            continue
        artist_key = normalize(match.artist)
        if artist_key in seen_artists:
            continue
        seen_artists.add(artist_key)
        candidates.append(match)
        if len(candidates) == MAX_ATLAS_CANDIDATES:
            break

    tracks = list(_search_pool.map(
        lambda match: _lookup_spotify_track(spotify, match.spotify_id),
        candidates,
    ))

    picks: list[Track] = []
    seen = {current} | ({track_uri} if track_uri else set())
    for track in tracks:
        if track is None:
            continue
        identity = _identity(track.title, track.primary_artist)
        if track.uri in seen or identity in seen:
            continue
        seen.update({track.uri, identity})
        picks.append(track)
        if len(picks) == MAX_RECOMMENDATIONS:
            break

    if not picks:
        return None

    reasons: list[str | None] = [None] * len(picks)
    if ai_service.is_configured():
        try:
            reasons = ai_service.explain_recommendations(
                artist, title, [(t.primary_artist, t.title) for t in picks]
            )
        except ai_service.AIServiceError as error:
            log.info("Could not write reasons for MusicAtlas picks: %s", error)

    return RecommendationResult(
        items=[Recommendation(track, reason) for track, reason in zip(picks, reasons)],
        source="musicatlas",
        tags=tuple(similar.tags),
    )


def _from_ai(
    spotify: spotipy.Spotify,
    artist: str,
    title: str,
    album: str | None,
    track_uri: str | None,
) -> RecommendationResult:
    suggestions = ai_service.suggest_similar_songs(artist, title, album)

    found = list(_search_pool.map(
        lambda s: find_on_spotify(spotify, s.title, s.artist),
        suggestions,
    ))

    current = _identity(title, artist)
    seen = {current}
    if track_uri:
        seen.add(track_uri)

    recommendations: list[Recommendation] = []
    for suggestion, track in zip(suggestions, found):
        if track is None:
            continue  # not on Spotify: probably made up
        identity = _identity(track.title, track.primary_artist)
        if track.uri in seen or identity in seen:
            continue
        seen.update({track.uri, identity})
        recommendations.append(Recommendation(track, suggestion.reason))
        if len(recommendations) == MAX_RECOMMENDATIONS:
            break

    return RecommendationResult(items=recommendations, source="ai")


def get_recommendations(
    spotify: spotipy.Spotify,
    artist: str,
    title: str,
    album: str | None = None,
    track_uri: str | None = None,
) -> RecommendationResult:
    """
    Up to three songs similar to the given one, each playable on Spotify.

    Raises:
        AINotConfiguredError: neither MusicAtlas nor the AI could be used.
        AIServiceError: the AI fallback failed.
    """
    key = (artist.strip(), title.strip(), (album or "").strip() or None)

    with _in_flight.lock(key):
        cached = _cache.get(key)
        if cached is not None:
            return cached

        result = _from_musicatlas(spotify, key[0], key[1], track_uri)

        if result is None:
            if not ai_service.is_configured():
                raise ai_service.AINotConfiguredError(
                    "No recommendation source available: set MUSICATLAS_API_KEY "
                    "or GEMINI_API_KEY in .env (MusicAtlas may also not know this song)."
                )
            result = _from_ai(spotify, *key, track_uri)

        _cache.set(key, result)
        return result


def clear_cache() -> None:
    _cache.clear()
