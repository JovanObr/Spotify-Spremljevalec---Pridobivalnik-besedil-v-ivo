"""
"If you like this song": AI suggestions checked against Spotify.

1. Gemini suggests up to five songs (services/ai_service.py).
2. Each suggestion is looked up with Spotify search, in parallel. Only songs
   whose title and artist match a real Spotify track are kept, which drops
   songs the AI made up or misattributed.
3. The current song and duplicates are removed, and the first three are
   returned with Spotify's track data and the AI's one-line reason.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import spotipy

from models.track import Track
from services import ai_service
from services.lyrics_service import clean_title
from utils.cache import TTLCache
from utils.single_flight import SingleFlight
from utils.text import normalize, same_name


MAX_RECOMMENDATIONS = 3

_cache = TTLCache(ttl_seconds=6 * 3600, max_size=256)
_in_flight = SingleFlight()
_search_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="rec-search")


@dataclass(frozen=True)
class Recommendation:
    track: Track
    reason: str

    def to_dict(self) -> dict:
        return {"track": self.track.to_dict(), "reason": self.reason}


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


def get_recommendations(
    spotify: spotipy.Spotify,
    artist: str,
    title: str,
    album: str | None = None,
    track_uri: str | None = None,
) -> list[Recommendation]:
    """
    Up to three songs similar to the given one, each playable on Spotify.

    Raises the same errors as ai_service.suggest_similar_songs.
    """
    key = (artist.strip(), title.strip(), (album or "").strip() or None)

    with _in_flight.lock(key):
        cached = _cache.get(key)
        if cached is not None:
            return cached

        suggestions = ai_service.suggest_similar_songs(*key)

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

        _cache.set(key, recommendations)
        return recommendations


def clear_cache() -> None:
    _cache.clear()
