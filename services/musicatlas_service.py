"""
MusicAtlas: similar songs from audio analysis (https://musicatlas.ai/developer).

POST https://musicatlas.ai/api/similar_tracks {artist, track} returns up to
20 similar songs with their Spotify IDs. Songs outside MusicAtlas's catalog
come back as HTTP 200 with "in_catalog": false.

The free plan allows 100 requests per rolling 24 hours, so results are
cached for a long time.
"""

from dataclasses import dataclass

import requests

from core.config import get_musicatlas_api_key
from utils.cache import TTLCache


BASE_URL = "https://musicatlas.ai/api"
REQUEST_TIMEOUT = 12

_session = requests.Session()
_session.headers.update({"Accept": "application/json"})

# "Not in catalog" and found results are both cached; failures are not
_cache = TTLCache(ttl_seconds=24 * 3600, max_size=512)


class MusicAtlasError(Exception):
    """MusicAtlas could not be used (bad key, quota, network, server)."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class SimilarTrack:
    artist: str
    title: str
    spotify_id: str | None


@dataclass(frozen=True)
class SimilarTracks:
    matches: list[SimilarTrack]
    # Style tags MusicAtlas gives for the source song, e.g. "dreampop"
    tags: list[str]
    in_catalog: bool = True


def is_configured() -> bool:
    return get_musicatlas_api_key() is not None


def _spotify_id(platform_ids) -> str | None:
    if not isinstance(platform_ids, dict):
        return None
    value = platform_ids.get("spotify")
    if isinstance(value, list):  # be tolerant of a list of IDs
        value = value[0] if value else None
    if not isinstance(value, str) or not value:
        return None
    # Accept bare IDs (documented) as well as URIs/URLs
    return value.rsplit(":", 1)[-1].rsplit("/", 1)[-1].split("?")[0]


def similar_tracks(artist: str, title: str) -> SimilarTracks:
    """
    Songs similar to artist + title.

    Raises:
        MusicAtlasError: no key, invalid key, quota reached, or the request failed.
    """
    api_key = get_musicatlas_api_key()
    if not api_key:
        raise MusicAtlasError("MUSICATLAS_API_KEY is not set.")

    key = (artist.strip().casefold(), title.strip().casefold())
    cached = _cache.get(key)
    if cached is not None:
        return cached

    try:
        response = _session.post(
            f"{BASE_URL}/similar_tracks",
            json={"artist": artist.strip(), "track": title.strip()},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        raise MusicAtlasError(f"MusicAtlas request failed: {error}") from error

    if response.status_code in (401, 403):
        raise MusicAtlasError("MusicAtlas rejected the API key.", response.status_code)
    if response.status_code == 429:
        raise MusicAtlasError("MusicAtlas daily limit reached.", 429)
    if response.status_code >= 400:
        raise MusicAtlasError(
            f"MusicAtlas returned HTTP {response.status_code}.", response.status_code
        )

    try:
        data = response.json()
    except ValueError as error:
        raise MusicAtlasError("MusicAtlas returned invalid JSON.") from error

    if not isinstance(data, dict):
        raise MusicAtlasError("MusicAtlas returned an unexpected response.")

    if data.get("in_catalog") is False or data.get("success") is False:
        result = SimilarTracks(matches=[], tags=[], in_catalog=False)
        _cache.set(key, result)
        return result

    matches = [
        SimilarTrack(
            artist=str(match.get("artist") or "").strip(),
            title=str(match.get("title") or "").strip(),
            spotify_id=_spotify_id(match.get("platform_ids")),
        )
        for match in data.get("matches") or []
        if isinstance(match, dict)
    ]
    tags = [
        str(tag).lstrip("#").strip()
        for tag in data.get("hashtags") or []
        if str(tag).strip()
    ]

    result = SimilarTracks(matches=[m for m in matches if m.title], tags=tags[:6])
    _cache.set(key, result)
    return result


def clear_cache() -> None:
    _cache.clear()
