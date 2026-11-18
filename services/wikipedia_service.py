"""
Song and artist details scraped from English Wikipedia (web scraping).

The service downloads ordinary Wikipedia pages (the search results page and
articles, as HTML) and reads them with BeautifulSoup, the same way as the
Naloga2 scraper:

1. Search page: Special:Search?search="<title>" <artist> song
2. The first few results are opened until one has a song infobox that
   names the artist ("Single by Queen", "Song by ...").
3. Its infobox rows (Released, Genre, Label, Songwriter(s) ...) become the
   song details. The artist link in the same infobox leads to the artist's
   article, whose infobox gives their origin, genres and years active.

Pages are fetched at most once per song/artist per week (cache) with a
descriptive User-Agent, as Wikipedia asks of automated clients.
"""

import re
import threading
from dataclasses import asdict, dataclass, field
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from services import source_registry
from services.lyrics_service import clean_title
from utils import persistent_cache
from utils.cache import TTLCache
from utils.single_flight import SingleFlight
from utils.text import normalize, same_name


BASE_URL = "https://en.wikipedia.org"
SEARCH_URL = f"{BASE_URL}/w/index.php"
USER_AGENT = (
    "SpotifySoundCompanion/1.0 (university student project; "
    "https://github.com/JovanObr/Spotify-Spremljevalec---Pridobivalnik-besedil-v-ivo)"
)
REQUEST_TIMEOUT = 10
MAX_CANDIDATES = 3  # articles opened per search, at most

CACHE_TTL = 7 * persistent_cache.DAY

# Infobox rows shown for a song, in this order (Wikipedia's own labels)
SONG_FIELDS = (
    "Released", "Recorded", "Studio", "Venue", "Genre", "Length", "Label",
    "Songwriter(s)", "Composer(s)", "Lyricist(s)", "Producer(s)",
)
ARTIST_FIELDS = ("Origin", "Born", "Genres", "Years active", "Labels", "Members")

# A song article's infobox says "Single by X", "Song by X", "Promotional single by X" ...
_SONG_HEADER = re.compile(r"\b(single|song|track|instrumental)\b.*\bby\b", re.I)

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT

_cache = TTLCache(ttl_seconds=CACHE_TTL, max_size=256)
_in_flight = SingleFlight()


class WikipediaError(Exception):
    """Wikipedia couldn't be reached or answered with an error."""


@dataclass
class InfoField:
    label: str
    values: list[str]


@dataclass
class SongDetails:
    title: str
    url: str
    album: str | None = None
    fields: list[InfoField] = field(default_factory=list)
    artist_url: str | None = None


@dataclass
class ArtistDetails:
    name: str
    url: str
    summary: str | None = None
    origin: str | None = None
    fields: list[InfoField] = field(default_factory=list)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _fetch(url: str, params: dict | None = None) -> BeautifulSoup:
    """Download one page and parse it."""
    with source_registry.tracking("wikipedia"):
        try:
            response = _session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as error:
            raise WikipediaError(f"Wikipedia could not be reached: {error}") from error
        if response.status_code == 404:
            return BeautifulSoup("", "html.parser")
        if response.status_code >= 400:
            raise WikipediaError(f"Wikipedia answered HTTP {response.status_code}.")
        return BeautifulSoup(response.text, "html.parser")


def search(query: str) -> list[str]:
    """Article URLs from Wikipedia's search results page, best first."""
    soup = _fetch(SEARCH_URL, {
        "search": query,
        "title": "Special:Search",
        "fulltext": "1",
        "ns0": "1",
    })
    urls = []
    for link in soup.select(".mw-search-result-heading a[href]"):
        href = link["href"]
        if href.startswith("/wiki/"):
            urls.append(urljoin(BASE_URL, href))
    return urls


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_BREAK = "\u2028"  # stands in for <br> while the text is joined


def _strip_junk(element: Tag) -> None:
    """Remove footnote markers, hidden spans and edit links (in place)."""
    for junk in element.select("sup, style, .noprint, .mw-editsection"):
        junk.decompose()
    for hidden in element.select('[style*="display:none"], [style*="display: none"]'):
        hidden.decompose()


def _tidy(text: str) -> str:
    text = re.sub(r"\[\s*(?:\d+|[a-z]|citation needed|note \d+)\s*\]", "", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _clean_text(element: Tag) -> str:
    """Visible text without footnote markers like [1] or [a]."""
    _strip_junk(element)
    return _tidy(element.get_text(" ", strip=True).replace(_BREAK, " "))


def _cell_values(cell: Tag) -> list[str]:
    """One infobox cell as a list: its list items, or its lines (<br>), or its text."""
    _strip_junk(cell)
    items = cell.select("li")
    if items:
        values = [_tidy(item.get_text(" ", strip=True)) for item in items]
    else:
        for br in cell.find_all("br"):
            br.replace_with(_BREAK)
        for block in cell.find_all("div"):
            block.insert_before(_BREAK)
        values = [_tidy(part) for part in cell.get_text(" ").split(_BREAK)]
    return [value for value in values if value]


def find_infobox(soup: BeautifulSoup) -> Tag | None:
    return soup.select_one("table.infobox")


def infobox_rows(infobox: Tag) -> dict[str, Tag]:
    """Label -> value cell, for rows with a label and a value."""
    rows = {}
    for row in infobox.select("tr"):
        label = row.find("th", class_="infobox-label") or row.find("th", scope="row")
        value = row.find("td", class_="infobox-data") or row.find("td")
        if label and value:
            rows[_clean_text(label).replace(" ", " ")] = value
    return rows


def infobox_headers(infobox: Tag) -> list[Tag]:
    return infobox.select(".infobox-header, .infobox-above, th[colspan]")


def parse_song(soup: BeautifulSoup, url: str, artist: str) -> SongDetails | None:
    """The song's details, if this page is a song article by `artist`."""
    infobox = find_infobox(soup)
    if infobox is None:
        return None

    artist_url = None
    by_header = None
    for header in infobox_headers(infobox):
        text = _clean_text(header)
        if _SONG_HEADER.search(text):
            by_header = header
            break
    if by_header is None:
        return None

    credited = _clean_text(by_header).split(" by ", 1)[-1]
    if not same_name(credited, artist) and not any(
        same_name(part, artist) for part in re.split(r",| and | & | featuring | feat\. ", credited)
    ):
        return None

    link = by_header.find("a", href=re.compile(r"^/wiki/[^:]+$"))
    if link:
        artist_url = urljoin(BASE_URL, link["href"])

    album = None
    for header in infobox_headers(infobox):
        text = _clean_text(header)
        match = re.match(r"(?:from the )?(?:album|EP|soundtrack|mixtape)\s+(.+)", text, re.I)
        if text.lower().startswith("from the") and match:
            album = match.group(1).strip()
            break

    title_cell = infobox.select_one(".infobox-above, caption")
    title = _clean_text(title_cell).strip('"“”') if title_cell else _title_from_url(url)

    rows = infobox_rows(infobox)
    fields = [
        InfoField(label, values)
        for label in SONG_FIELDS
        if label in rows and (values := _cell_values(rows[label]))
    ]
    return SongDetails(title=title, url=url, album=album, fields=fields, artist_url=artist_url)


def parse_artist(soup: BeautifulSoup, url: str) -> ArtistDetails | None:
    """The artist's details, if this page is about a musician or band."""
    infobox = find_infobox(soup)
    if infobox is None:
        return None
    rows = infobox_rows(infobox)
    if not any(label in rows for label in ("Origin", "Genres", "Years active", "Instrument(s)", "Labels")):
        return None

    fields = [
        InfoField(label, values)
        for label in ARTIST_FIELDS
        if label in rows and (values := _cell_values(rows[label]))
    ]

    origin = None
    if "Origin" in rows:
        origin = _clean_text(rows["Origin"])
    elif "Born" in rows:
        place = rows["Born"].select_one(".birthplace")
        if place:
            origin = _clean_text(place)
        else:
            lines = _cell_values(rows["Born"])
            origin = lines[-1] if len(lines) > 1 else None

    name_cell = infobox.select_one(".infobox-above, caption")
    name = _clean_text(name_cell) if name_cell else _title_from_url(url)

    return ArtistDetails(
        name=name,
        url=url,
        summary=_lead_summary(soup),
        origin=origin,
        fields=fields,
    )


def _lead_summary(soup: BeautifulSoup, max_chars: int = 320) -> str | None:
    """The first sentence or two of the article."""
    content = soup.select_one(".mw-parser-output") or soup
    for paragraph in content.find_all("p", recursive=True):
        if "mw-empty-elt" in (paragraph.get("class") or []):
            continue
        text = _clean_text(paragraph)
        if len(text) < 40:
            continue
        # Drop the pronunciation/birth-date bracket after the name
        first = re.search(r"\s*\((?:[^()]|\([^()]*\))*\)", text)
        if first and re.search(r"born|;|/|pronounced", first.group(0)):
            text = text[: first.start()] + text[first.end():]
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        summary = sentences[0]
        if len(sentences) > 1 and len(summary) + len(sentences[1]) < max_chars:
            summary += " " + sentences[1]
        return summary[:max_chars].rstrip()
    return None


def _title_from_url(url: str) -> str:
    return unquote(url.rsplit("/", 1)[-1]).replace("_", " ")


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def find_song(artist: str, title: str) -> SongDetails | None:
    """The Wikipedia article for this song, or None."""
    short = clean_title(title)
    for url in search(f'"{short}" {artist} song')[:MAX_CANDIDATES]:
        details = parse_song(_fetch(url), url, artist)
        if details and (same_name(details.title, short) or normalize(short) in normalize(details.title)):
            return details
    return None


def find_artist(artist: str, url: str | None = None) -> ArtistDetails | None:
    """The artist's article: from a known link, or by searching."""
    if url:
        details = parse_artist(_fetch(url), url)
        if details:
            return details

    for candidate in search(f"{artist} musician band singer")[:MAX_CANDIDATES]:
        if not same_name(_title_from_url(candidate).split(" (")[0], artist):
            continue
        details = parse_artist(_fetch(candidate), candidate)
        if details:
            return details
    return None


@dataclass
class Details:
    song: SongDetails | None
    artist: ArtistDetails | None

    def to_dict(self) -> dict:
        return {
            "song": asdict(self.song) if self.song else None,
            "artist": asdict(self.artist) if self.artist else None,
        }


def _decode(data: dict) -> Details:
    def fields(items):
        return [InfoField(**item) for item in items]

    song = data.get("song")
    artist = data.get("artist")
    return Details(
        song=SongDetails(**{**song, "fields": fields(song["fields"])}) if song else None,
        artist=ArtistDetails(**{**artist, "fields": fields(artist["fields"])}) if artist else None,
    )


def get_details(artist: str, title: str) -> Details:
    """
    Song and artist details (either can be None). Cached for a week, on
    disk too.

    Raises:
        ValueError: empty artist or title.
        WikipediaError: Wikipedia couldn't be reached.
    """
    artist, title = artist.strip(), title.strip()
    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    key = (normalize(artist), normalize(clean_title(title)))
    with _in_flight.lock(key):
        cached = _cache.get(key)
        if cached is not None:
            return cached

        stored = persistent_cache.store().get("wikipedia", list(key))
        if stored is not persistent_cache.MISSING:
            try:
                details = _decode(stored)
                _cache.set(key, details)
                return details
            except (KeyError, TypeError):
                pass

        song = find_song(artist, title)
        artist_details = find_artist(artist, song.artist_url if song else None)
        details = Details(song=song, artist=artist_details)

        _cache.set(key, details)
        persistent_cache.store().set("wikipedia", list(key), details.to_dict(), CACHE_TTL)
        return details


def clear_cache() -> None:
    _cache.clear()
    persistent_cache.store().clear("wikipedia")
