"""
Every outside data source the app uses, which technology reaches it, how
often its data is refreshed, and when it last answered.

The services report each request (success or failure) here, and the
"Data sources" page shows the result (GET /api/sources). Times are kept in
the persistent cache too, so the page still knows after a restart when the
data it serves from the cache was fetched.
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

from utils import persistent_cache


@dataclass(frozen=True)
class SourceInfo:
    id: str
    name: str
    technology: str
    format: str
    provides: str
    refresh: str
    url: str
    # Can the user force a refetch? Not for quota-limited sources.
    refreshable: bool = True


SOURCES: tuple[SourceInfo, ...] = (
    SourceInfo(
        id="spotify",
        name="Spotify Web API",
        technology="REST",
        format="JSON, OAuth 2.0",
        provides="Now playing, playback control, search, playlists, liked and recently played songs",
        refresh="Player state every 3 seconds; library lists every 30 to 60 seconds",
        url="https://developer.spotify.com/documentation/web-api",
    ),
    SourceInfo(
        id="lrclib",
        name="LRCLIB",
        technology="REST",
        format="JSON",
        provides="Synced (timed) lyrics",
        refresh="Once per song, kept 90 days; songs without lyrics are checked again after 3 days",
        url="https://lrclib.net",
    ),
    SourceInfo(
        id="lyrics_ovh",
        name="lyrics.ovh",
        technology="REST",
        format="JSON",
        provides="Plain lyrics when LRCLIB has none",
        refresh="Once per song, kept 90 days",
        url="https://lyricsovh.docs.apiary.io",
    ),
    SourceInfo(
        id="wikipedia",
        name="Wikipedia",
        technology="Web scraping",
        format="HTML, parsed with BeautifulSoup",
        provides="Song details (release, genre, label, writers, producers) and the artist's origin",
        refresh="Once per song or artist, kept 7 days",
        url="https://en.wikipedia.org",
    ),
    SourceInfo(
        id="countryinfo",
        name="CountryInfoService",
        technology="SOAP",
        format="XML (SOAP 1.1 envelopes)",
        provides="The artist's country: flag, capital, language, currency",
        refresh="Country list and details kept 30 days",
        url="http://webservices.oorsprong.org/websamples.countryinfo/CountryInfoService.wso?WSDL",
    ),
    SourceInfo(
        id="sistat",
        name="SiStat (Statistical Office of Slovenia)",
        technology="PC-Axis",
        format=".px file from the PX-Web API",
        provides="Music in Slovenia: performances and attendance by type of music, 2016 to 2024 (table 1080711S)",
        refresh="Checked every 24 hours (SiStat updates it yearly)",
        url="https://pxweb.stat.si/SiStat",
    ),
    SourceInfo(
        id="gemini",
        name="Google AI Studio (Gemini, Gemma)",
        technology="REST",
        format="JSON with a response schema",
        provides="Song facts, translations, song meanings, recommendation reasons",
        refresh="Once per song and language, kept 90 days",
        url="https://aistudio.google.com",
        refreshable=False,  # each refetch uses the free daily quota
    ),
    SourceInfo(
        id="musicatlas",
        name="MusicAtlas",
        technology="REST",
        format="JSON",
        provides="Songs that sound similar, and style tags",
        refresh="Once per song, kept 30 days (100 requests a day on the free plan)",
        url="https://musicatlas.ai",
        refreshable=False,
    ),
)

BY_ID = {source.id: source for source in SOURCES}

# Writing to disk on every Spotify poll would be wasteful
PERSIST_EVERY_SECONDS = 60
STATUS_TTL = 365 * persistent_cache.DAY


@dataclass
class _Status:
    last_success: float | None = None
    last_failure: float | None = None
    last_error: str | None = None
    requests: int = 0
    persisted_at: float = 0.0


_lock = threading.Lock()
_status: dict[str, _Status] = {}


def _get(source_id: str) -> _Status:
    status = _status.get(source_id)
    if status is None:
        status = _Status()
        stored = persistent_cache.store().get("sources", source_id)
        if isinstance(stored, dict):
            status.last_success = stored.get("last_success")
            status.last_failure = stored.get("last_failure")
            status.last_error = stored.get("last_error")
        _status[source_id] = status
    return status


def _persist(source_id: str, status: _Status, force: bool) -> None:
    now = time.time()
    if not force and now - status.persisted_at < PERSIST_EVERY_SECONDS:
        return
    status.persisted_at = now
    persistent_cache.store().set(
        "sources",
        source_id,
        {
            "last_success": status.last_success,
            "last_failure": status.last_failure,
            "last_error": status.last_error,
        },
        STATUS_TTL,
    )


def record_success(source_id: str) -> None:
    with _lock:
        status = _get(source_id)
        status.last_success = time.time()
        status.requests += 1
        _persist(source_id, status, force=False)


def record_failure(source_id: str, error: BaseException | str) -> None:
    with _lock:
        status = _get(source_id)
        status.last_failure = time.time()
        status.last_error = str(error)[:300]
        status.requests += 1
        _persist(source_id, status, force=True)


@contextmanager
def tracking(source_id: str):
    """Wrap one request to a source: records whether it worked."""
    try:
        yield
    except Exception as error:
        record_failure(source_id, error)
        raise
    else:
        record_success(source_id)


def describe() -> list[dict]:
    """Every source with its current status, for the Data sources page."""
    now = time.time()
    result = []
    with _lock:
        for source in SOURCES:
            status = _get(source.id)
            ok = status.last_success is not None and (
                status.last_failure is None or status.last_success >= status.last_failure
            )
            if status.last_success is None and status.last_failure is None:
                state = "unused"
            else:
                state = "ok" if ok else "error"
            result.append({
                "id": source.id,
                "name": source.name,
                "technology": source.technology,
                "format": source.format,
                "provides": source.provides,
                "refresh": source.refresh,
                "url": source.url,
                "refreshable": source.refreshable,
                "state": state,
                "last_success": status.last_success,
                "last_failure": status.last_failure,
                "last_error": status.last_error if state == "error" else None,
                "requests_this_run": status.requests,
                "checked_at": now,
            })
    return result


def reset() -> None:
    """Forget all statuses in memory (tests)."""
    with _lock:
        _status.clear()
