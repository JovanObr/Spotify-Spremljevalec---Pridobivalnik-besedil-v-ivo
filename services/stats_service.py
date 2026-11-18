"""
"Music in Slovenia": a SiStat table downloaded as a PC-Axis (.px) file.

SiStat (the Statistical Office of Slovenia) publishes its tables through
PX-Web. Its API answers two calls per table:

    GET  .../api/v1/en/Data/<path>/<table>.px   the table's dimensions (JSON)
    POST .../api/v1/en/Data/<path>/<table>.px   the data, in the format asked
                                                for: here "px", PC-Axis

The .px file is parsed with utils/pcaxis.py and turned into a compact JSON
shape for the page: the dimensions with their values, and every cell as
[index in dimension 1, index in dimension 2, ..., value].

SiStat updates such tables about once a year, so the file is fetched again
every 24 hours. If SiStat can't be reached, the last copy is shown and
marked as stale.
"""

import os
import threading
import time

import requests

from services import source_registry
from utils import pcaxis, persistent_cache


API_BASE = "https://pxweb.stat.si/SiStatData/api/v1/en/Data"
SITE_BASE = "https://pxweb.stat.si/SiStatData/pxweb/en/Data/-"
# The table shown on the page: "Performances and attendance in institutions
# with stage activity by type of performances, Slovenia, 2016 - 2024"
# (24 types of performance x number of performances / attendance x year).
# SiStat's database is flat, so the path is just the table's file name.
# SISTAT_TABLE in .env can point the page at another table.
DEFAULT_TABLE = "1080711S.px"
REFRESH_SECONDS = 24 * 3600
KEEP_SECONDS = 365 * persistent_cache.DAY  # last good copy, for when SiStat is down
REQUEST_TIMEOUT = 20
MAX_CELLS = 50_000

_session = requests.Session()
_session.headers["User-Agent"] = "SpotifySoundCompanion/1.0 (university student project)"
_lock = threading.Lock()
_memory: dict | None = None


class StatsError(Exception):
    """SiStat couldn't be reached or sent something unusable."""


class StatsNotConfigured(StatsError):
    pass


def table_path() -> str:
    return (os.getenv("SISTAT_TABLE") or DEFAULT_TABLE).strip().strip("/")


def _post_query(metadata: dict) -> dict:
    """Ask for every value of every dimension."""
    return {
        "query": [
            {"code": variable["code"], "selection": {"filter": "all", "values": ["*"]}}
            for variable in metadata.get("variables", [])
        ],
        "response": {"format": "px"},
    }


def download(path: str) -> bytes:
    """The table as a .px file."""
    url = f"{API_BASE}/{path}"
    with source_registry.tracking("sistat"):
        try:
            meta_response = _session.get(url, timeout=REQUEST_TIMEOUT)
            meta_response.raise_for_status()
            metadata = meta_response.json()
            cells = 1
            for variable in metadata.get("variables", []):
                cells *= max(1, len(variable.get("values", [])))
            if cells > MAX_CELLS:
                raise StatsError(f"The table has {cells} cells; the page shows at most {MAX_CELLS}.")

            response = _session.post(url, json=_post_query(metadata), timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as error:
            raise StatsError(f"SiStat could not be reached: {error}") from error
        except ValueError as error:
            raise StatsError("SiStat sent an unreadable table description.") from error
        return response.content


def _year_like(values: list[str]) -> bool:
    return bool(values) and all(value[:4].isdigit() for value in values)


def to_json(table: pcaxis.PxTable, path: str) -> dict:
    """The compact shape the page uses."""
    names = [name for name, _ in table.dimensions]
    index = [{label: i for i, label in enumerate(labels)} for _, labels in table.dimensions]

    time_dimension = next(
        (
            name for name, labels in table.dimensions
            if any(word in name.lower() for word in ("year", "leto", "time", "period", "season"))
            or _year_like(labels)
        ),
        None,
    )

    observations = [
        [*(index[i][label] for i, label in enumerate(key)), value]
        for key, value in table.data.items()
    ]

    return {
        "title": table.title,
        "contents": table.contents,
        "units": table.units,
        "source": table.source,
        "last_updated": table.last_updated,
        "notes": table.notes,
        "table": path,
        "table_url": f"{SITE_BASE}/{path}",
        "time_dimension": time_dimension,
        "dimensions": [{"name": name, "values": labels} for name, labels in table.dimensions],
        "observations": observations,
        "dimension_names": names,
    }


def get_stats(force: bool = False) -> dict:
    """
    The table, at most 24 hours old (or the last copy if SiStat is down).

    Raises:
        StatsNotConfigured: no table chosen.
        StatsError: SiStat failed and there's no earlier copy.
    """
    global _memory
    path = table_path()
    if not path:
        raise StatsNotConfigured("No SiStat table is configured (SISTAT_TABLE).")

    with _lock:
        saved = _memory
        if saved is None or saved.get("table") != path:
            stored = persistent_cache.store().get("sistat", path)
            saved = stored if isinstance(stored, dict) else None

        if saved and not force and time.time() - saved["fetched_at"] < REFRESH_SECONDS:
            _memory = saved
            return {**saved, "stale": False}

        try:
            table = pcaxis.parse(download(path), language="en")
        except (StatsError, pcaxis.PxError) as error:
            if saved:
                return {**saved, "stale": True, "error": str(error)}
            if isinstance(error, pcaxis.PxError):
                raise StatsError(f"SiStat's file couldn't be read: {error}") from error
            raise

        fresh = {**to_json(table, path), "fetched_at": time.time()}
        _memory = fresh
        persistent_cache.store().set("sistat", path, fresh, KEEP_SECONDS)
        return {**fresh, "stale": False}


def clear_cache() -> None:
    """Make the next request fetch the table again (keeps the copy for outages)."""
    global _memory
    with _lock:
        if _memory:
            _memory = {**_memory, "fetched_at": 0}
        stored = persistent_cache.store().get("sistat", table_path())
        if isinstance(stored, dict):
            persistent_cache.store().set("sistat", table_path(), {**stored, "fetched_at": 0}, KEEP_SECONDS)
