"""
Lyrics lookup.

Sources are tried in order (LYRICS_PROVIDERS, default "lrclib,lyricsovh"):

1. LRCLIB: a community database with time-synced lyrics. Several search
   strategies are tried, from exact to fuzzy, and a synced version is
   preferred over plain text.
2. lyrics.ovh: a public API with plain (not synced) lyrics, used when LRCLIB
   has nothing.

Adding a source = writing one function `(query) -> Lyrics | None` and
registering it in PROVIDERS, saying whether it can return synced lyrics.
"""

import re

from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote

import requests

from core.config import get_lyrics_providers
from utils.cache import TTLCache
from utils.single_flight import SingleFlight
from utils.text import normalize, same_name as _same_name  # noqa: F401 (normalize re-exported)


BASE_URL = "https://lrclib.net/api"
LYRICS_OVH_URL = "https://api.lyrics.ovh/v1"
REQUEST_TIMEOUT = 10
LYRICS_OVH_TIMEOUT = 8

# How far (in seconds) a search result's duration may differ from Spotify's.
DURATION_TOLERANCE_SECONDS = 5

USER_AGENT = (
    "Spotify-Spremljevalec/0.1 "
    "(https://github.com/JovanObr/"
    "Spotify-Spremljevalec---Pridobivalnik-besedil-v-ivo)"
)

# One shared session reuses the TCP/TLS connection between requests.
_session = requests.Session()
_session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
})


@dataclass(frozen=True)
class LyricLine:
    time_ms: int
    text: str


@dataclass
class Lyrics:
    track_name: str
    artist_name: str
    album_name: str | None
    plain_lyrics: str | None
    synced_lyrics: str | None
    instrumental: bool
    source: str = "LRCLIB"
    lines: list[LyricLine] = field(default_factory=list)

    def __post_init__(self):
        if self.synced_lyrics and not self.lines:
            self.lines = parse_synced_lyrics(self.synced_lyrics)

    def to_dict(self) -> dict:
        return {
            "track_name": self.track_name,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "instrumental": self.instrumental,
            "plain_lyrics": self.plain_lyrics,
            "lines": [
                {"time_ms": line.time_ms, "text": line.text}
                for line in self.lines
            ],
            "source": self.source,
        }


class LyricsServiceError(Exception):
    """Raised when no lyrics source could be reached or used."""


class LyricsRateLimitError(LyricsServiceError):
    """Raised when a lyrics source rate-limits the application."""

    def __init__(self, retry_after: str | None = None, source: str = "LRCLIB"):
        self.retry_after = retry_after
        super().__init__(f"{source} rate limit reached.")


# ---------------------------------------------------------------------------
# Synced lyrics (LRC) parsing
# ---------------------------------------------------------------------------

_TIMESTAMP = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")


def parse_synced_lyrics(lrc: str) -> list[LyricLine]:
    """
    Parse LRC text ("[01:23.45] line") into time-ordered lines.

    Supports several timestamps per line and ignores metadata tags
    such as [ar:Artist].
    """
    lines: list[LyricLine] = []

    for raw_line in lrc.splitlines():
        timestamps = []
        position = 0

        while match := _TIMESTAMP.match(raw_line, position):
            minutes, seconds, fraction = match.groups()
            # ".5" -> 500 ms, ".45" -> 450 ms, ".456" -> 456 ms
            millis = int((fraction or "0").ljust(3, "0")[:3])
            timestamps.append(
                (int(minutes) * 60 + int(seconds)) * 1000 + millis
            )
            position = match.end()

        text = raw_line[position:].strip()

        for time_ms in timestamps:
            lines.append(LyricLine(time_ms=time_ms, text=text))

    lines.sort(key=lambda line: line.time_ms)
    return lines


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

# " - Remastered 2011", " - Live", " (feat. X)", " [Radio Edit]" ...
_TITLE_NOISE = re.compile(
    r"\s+-\s+.*$"
    r"|\s*[(\[](?:feat\.?|ft\.?|with|from|remaster|remastered|live|"
    r"radio edit|single version|album version|mono|stereo)[^)\]]*[)\]]",
    re.IGNORECASE,
)


def clean_title(title: str) -> str:
    """Strip Spotify-style suffixes that lyrics databases usually don't have."""
    cleaned = _TITLE_NOISE.sub("", title).strip()
    return cleaned or title


@dataclass(frozen=True)
class LyricsQuery:
    artist: str
    title: str
    album: str | None
    duration_seconds: int | None

    @property
    def short_title(self) -> str:
        return clean_title(self.title)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _get_json(url: str, params: dict | None, source: str, timeout: float):
    try:
        response = _session.get(url, params=params, timeout=timeout)

        if response.status_code == 404:
            return None

        if response.status_code == 429:
            raise LyricsRateLimitError(
                response.headers.get("Retry-After"), source
            )

        response.raise_for_status()

        return response.json()

    except LyricsRateLimitError:
        raise

    except requests.RequestException as error:
        raise LyricsServiceError(
            f"Could not retrieve lyrics from {source}: {error}"
        ) from error

    except ValueError as error:
        raise LyricsServiceError(
            f"{source} returned an invalid JSON response."
        ) from error


def _request(path: str, params: dict):
    """Call an LRCLIB endpoint."""
    return _get_json(f"{BASE_URL}/{path}", params, "LRCLIB", REQUEST_TIMEOUT)


# ---------------------------------------------------------------------------
# Provider 1: LRCLIB
# ---------------------------------------------------------------------------

def _to_lyrics(data: dict, title: str, artist: str, album: str | None):
    instrumental = bool(data.get("instrumental", False))
    plain_lyrics = data.get("plainLyrics")
    synced_lyrics = data.get("syncedLyrics")

    if not instrumental and not plain_lyrics and not synced_lyrics:
        return None

    return Lyrics(
        track_name=data.get("trackName", title),
        artist_name=data.get("artistName", artist),
        album_name=data.get("albumName", album),
        plain_lyrics=plain_lyrics,
        synced_lyrics=synced_lyrics,
        instrumental=instrumental,
    )


def _duration_ok(item: dict, duration_seconds: int | None) -> bool:
    return (
        duration_seconds is None
        or item.get("duration") is None
        or abs(item["duration"] - duration_seconds) <= DURATION_TOLERANCE_SECONDS
    )


def _pick_best(results: list, duration_seconds: int | None) -> dict | None:
    """Choose the closest-duration result, preferring synced lyrics."""

    candidates = [
        item for item in results
        if isinstance(item, dict)
        and (item.get("syncedLyrics") or item.get("plainLyrics") or item.get("instrumental"))
        and _duration_ok(item, duration_seconds)
    ]

    if not candidates:
        return None

    def score(item: dict):
        duration_gap = (
            abs(item["duration"] - duration_seconds)
            if duration_seconds is not None and item.get("duration")
            else 0
        )
        return (not item.get("syncedLyrics"), duration_gap)

    return min(candidates, key=score)


def lrclib_provider(query: LyricsQuery) -> Lyrics | None:
    """
    Try LRCLIB from most to least precise. Stops at the first synced
    match; a plain-only match is kept as a fallback while looking further.
    """
    fallback: Lyrics | None = None
    seen: set = set()

    def consider(data: dict | None) -> Lyrics | None:
        nonlocal fallback
        if not data:
            return None
        lyrics = _to_lyrics(data, query.title, query.artist, query.album)
        if lyrics and (lyrics.synced_lyrics or lyrics.instrumental):
            return lyrics
        if lyrics and fallback is None:
            fallback = lyrics
        return None

    def once(path: str, params: dict):
        key = (path, tuple(sorted(params.items())))
        if key in seen:
            return None
        seen.add(key)
        return _request(path, params)

    exact = {"artist_name": query.artist, "track_name": query.title}
    if query.duration_seconds is not None:
        exact["duration"] = query.duration_seconds

    # 1) Exact match, with the album
    if query.album:
        data = once("get", {**exact, "album_name": query.album})
        if data is not None and not isinstance(data, dict):
            raise LyricsServiceError("LRCLIB returned an unexpected response.")
        if found := consider(data):
            return found

    # 2) Exact match without the album (singles, compilations, deluxe editions)
    data = once("get", exact)
    if data is not None and not isinstance(data, dict):
        raise LyricsServiceError("LRCLIB returned an unexpected response.")
    if found := consider(data):
        return found

    searches = [
        # 3) Artist + cleaned title ("Song - Remastered 2011" -> "Song")
        ({"artist_name": query.artist, "track_name": query.short_title}, False),
        # 4) Free text: tolerates different artist spellings and "feat." in titles
        ({"q": f"{query.artist} {query.short_title}"}, True),
        # 5) Title only, then keep results whose artist looks the same
        ({"q": query.short_title}, True),
    ]

    for params, check_names in searches:
        results = once("search", params)
        if not isinstance(results, list):
            continue

        if check_names:
            results = [
                item for item in results
                if isinstance(item, dict)
                and _same_name(item.get("trackName"), query.short_title)
                and _same_name(item.get("artistName"), query.artist)
            ]

        best = _pick_best(results, query.duration_seconds)
        if found := consider(best):
            return found

    return fallback


# ---------------------------------------------------------------------------
# Provider 2: lyrics.ovh (plain lyrics only)
# ---------------------------------------------------------------------------

_OVH_HEADER = re.compile(r"^\s*Paroles de la chanson .*? par .*?\r?\n", re.IGNORECASE)


def _clean_plain(text: str) -> str:
    text = _OVH_HEADER.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def lyrics_ovh_provider(query: LyricsQuery) -> Lyrics | None:
    url = (
        f"{LYRICS_OVH_URL}/{quote(query.artist, safe='')}"
        f"/{quote(query.short_title, safe='')}"
    )
    data = _get_json(url, None, "lyrics.ovh", LYRICS_OVH_TIMEOUT)

    text = _clean_plain((data or {}).get("lyrics") or "") if isinstance(data, dict) else ""
    if not text:
        return None

    return Lyrics(
        track_name=query.title,
        artist_name=query.artist,
        album_name=query.album,
        plain_lyrics=text,
        synced_lyrics=None,
        instrumental=False,
        source="lyrics.ovh",
    )


@dataclass(frozen=True)
class Provider:
    find: Callable[[LyricsQuery], "Lyrics | None"]
    # Plain-only sources are skipped once plain lyrics were already found
    has_synced: bool


PROVIDERS = {
    "lrclib": Provider(lrclib_provider, has_synced=True),
    "lyricsovh": Provider(lyrics_ovh_provider, has_synced=False),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Found lyrics and "not found" are both cached; failed lookups are not.
_cache = TTLCache(ttl_seconds=6 * 3600, max_size=512)
_in_flight = SingleFlight()


def _lookup(query: LyricsQuery) -> tuple[Lyrics | None, bool]:
    """Run the providers in order. Returns (lyrics, every_source_answered)."""

    plain_fallback: Lyrics | None = None
    errors: list[LyricsServiceError] = []

    for name in get_lyrics_providers():
        provider = PROVIDERS.get(name)
        if provider is None or (plain_fallback and not provider.has_synced):
            continue

        try:
            lyrics = provider.find(query)
        except LyricsServiceError as error:
            errors.append(error)
            continue

        if lyrics is None:
            continue
        if lyrics.synced_lyrics or lyrics.instrumental:
            return lyrics, not errors
        plain_fallback = plain_fallback or lyrics

    if plain_fallback:
        return plain_fallback, not errors

    if errors:
        # Nothing found and at least one source failed: report it, so the
        # frontend retries later instead of showing "no lyrics"
        raise next(
            (e for e in errors if isinstance(e, LyricsRateLimitError)),
            errors[0],
        )

    return None, True


def get_lyrics(
    artist: str,
    title: str,
    album: str | None = None,
    duration_ms: int | None = None,
) -> Lyrics | None:
    """
    Find lyrics for a song, trying each source in LYRICS_PROVIDERS.

    Synced lyrics are preferred; plain lyrics are returned when that's all
    any source has. Results are cached for a few hours.

    Returns:
        Lyrics: A matching lyrics record.
        None: No source has lyrics for this song.

    Raises:
        ValueError: Invalid track information.
        LyricsRateLimitError: A source rate-limited us and nothing was found.
        LyricsServiceError: Sources failed and nothing was found.
    """

    artist = artist.strip()
    title = title.strip()
    album = album.strip() if album else None

    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    duration_seconds = None

    if duration_ms is not None:
        if duration_ms <= 0:
            raise ValueError("Duration must be positive.")

        duration_seconds = round(duration_ms / 1000)

        # LRCLIB only accepts 1-3600 s; longer tracks are looked up without it
        if not 1 <= duration_seconds <= 3600:
            duration_seconds = None

    query = LyricsQuery(artist, title, album, duration_seconds)

    # If the same song is already being looked up (e.g. prefetching), wait
    # for that lookup and use its cached result
    with _in_flight.lock(query):
        if _cache.has(query):
            return _cache.get(query)

        lyrics, complete = _lookup(query)

        if complete:
            _cache.set(query, lyrics)

        return lyrics


def clear_cache() -> None:
    """Forget cached lyrics (used by tests)."""
    _cache.clear()
