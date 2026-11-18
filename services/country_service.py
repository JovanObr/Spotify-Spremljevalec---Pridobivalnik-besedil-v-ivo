"""
Country details from CountryInfoService, a public SOAP web service
(http://webservices.oorsprong.org/websamples.countryinfo).

SOAP works differently from the REST APIs the rest of the app uses: every
call is an HTTP POST of an XML "envelope" naming the operation and its
parameters, described by the service's WSDL, and the answer is an XML
envelope too. The two operations used here:

- ListOfCountryNamesByName: every country's ISO code and English name,
  used to turn the origin from Wikipedia ("London, England") into a code.
- FullCountryInfo(sCountryISOCode): name, capital, phone code, continent,
  currency, flag image and languages.

Answers are kept for 30 days: country data changes very rarely.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from xml.sax.saxutils import escape

import requests

from services import source_registry
from utils import persistent_cache
from utils.cache import TTLCache
from utils.text import normalize


ENDPOINT = "http://webservices.oorsprong.org/websamples.countryinfo/CountryInfoService.wso"
WSDL_URL = f"{ENDPOINT}?WSDL"
SERVICE_NS = "http://www.oorsprong.org/websamples.countryinfo"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
REQUEST_TIMEOUT = 10
CACHE_TTL = 30 * persistent_cache.DAY

_session = requests.Session()
_session.headers["User-Agent"] = "SpotifySoundCompanion/1.0 (university student project)"
_cache = TTLCache(ttl_seconds=CACHE_TTL, max_size=300)


class CountryServiceError(Exception):
    """The SOAP service failed or answered with a SOAP Fault."""


@dataclass
class CountryInfo:
    iso_code: str
    name: str
    capital: str | None
    phone_code: str | None
    continent: str | None
    currency: str | None
    flag_url: str | None
    languages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# SOAP plumbing
# ---------------------------------------------------------------------------

def envelope(operation: str, params: dict[str, str] | None = None) -> str:
    """A SOAP 1.1 request envelope for one operation."""
    body = "".join(
        f"<{name}>{escape(value)}</{name}>" for name, value in (params or {}).items()
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<soap:Envelope xmlns:soap="{SOAP_NS}">'
        "<soap:Body>"
        f'<{operation} xmlns="{SERVICE_NS}">{body}</{operation}>'
        "</soap:Body>"
        "</soap:Envelope>"
    )


def call(operation: str, params: dict[str, str] | None = None) -> ET.Element:
    """
    POST one operation and return its <...Result> element.

    Raises:
        CountryServiceError: network error, HTTP error, SOAP Fault or bad XML.
    """
    with source_registry.tracking("countryinfo"):
        try:
            response = _session.post(
                ENDPOINT,
                data=envelope(operation, params).encode("utf-8"),
                headers={"Content-Type": "text/xml; charset=utf-8"},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as error:
            raise CountryServiceError(f"CountryInfoService could not be reached: {error}") from error

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as error:
            raise CountryServiceError(
                f"CountryInfoService answered HTTP {response.status_code} without valid XML."
            ) from error

        fault = root.find(f".//{{{SOAP_NS}}}Fault")
        if fault is not None:
            message = fault.findtext("faultstring") or "SOAP Fault"
            raise CountryServiceError(f"CountryInfoService: {message}")
        if response.status_code >= 400:
            raise CountryServiceError(f"CountryInfoService answered HTTP {response.status_code}.")

        result = root.find(f".//{{{SERVICE_NS}}}{operation}Result")
        if result is None:
            raise CountryServiceError(f"CountryInfoService sent no {operation}Result.")
        return result


def _text(element: ET.Element, name: str) -> str | None:
    value = element.findtext(f"{{{SERVICE_NS}}}{name}")
    return value.strip() if value and value.strip() else None


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def list_countries() -> list[tuple[str, str]]:
    """(ISO code, name) for every country the service knows."""

    def fetch():
        stored = persistent_cache.store().get("countryinfo", "list")
        if stored is not persistent_cache.MISSING:
            return [tuple(item) for item in stored]
        result = call("ListOfCountryNamesByName")
        countries = [
            (code, name)
            for item in result.findall(f"{{{SERVICE_NS}}}tCountryCodeAndName")
            if (code := _text(item, "sISOCode")) and (name := _text(item, "sName"))
        ]
        if countries:
            persistent_cache.store().set("countryinfo", "list", countries, CACHE_TTL)
        return countries

    return _cache.get_or_set("list", fetch)


def country_info(iso_code: str) -> CountryInfo:
    """Full details of one country (FullCountryInfo)."""
    iso_code = iso_code.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", iso_code):
        raise ValueError("Country code must be two letters.")

    def fetch():
        stored = persistent_cache.store().get("countryinfo", iso_code)
        if stored is not persistent_cache.MISSING:
            return CountryInfo(**stored)
        result = call("FullCountryInfo", {"sCountryISOCode": iso_code})
        name = _text(result, "sName")
        if not name or name.lower().startswith("country not found"):
            raise CountryServiceError(f"CountryInfoService doesn't know {iso_code}.")
        languages = [
            language
            for item in result.iter(f"{{{SERVICE_NS}}}tLanguage")
            if (language := _text(item, "sName"))
        ]
        info = CountryInfo(
            iso_code=_text(result, "sISOCode") or iso_code,
            name=name,
            capital=_text(result, "sCapitalCity"),
            phone_code=_text(result, "sPhoneCode"),
            continent=_text(result, "sContinentCode"),
            currency=_text(result, "sCurrencyISOCode"),
            flag_url=_text(result, "sCountryFlag"),
            languages=languages,
        )
        persistent_cache.store().set("countryinfo", iso_code, info.to_dict(), CACHE_TTL)
        return info

    return _cache.get_or_set(("info", iso_code), fetch)


# ---------------------------------------------------------------------------
# From a Wikipedia origin to a country
# ---------------------------------------------------------------------------

# Names Wikipedia uses that aren't the service's country names
ALIASES = {
    "england": "GB", "scotland": "GB", "wales": "GB", "northern ireland": "GB",
    "uk": "GB", "u.k.": "GB", "united kingdom": "GB", "great britain": "GB", "britain": "GB",
    "us": "US", "u.s.": "US", "usa": "US", "u.s.a.": "US", "united states": "US",
    "united states of america": "US", "america": "US",
    "south korea": "KR", "korea": "KR", "north korea": "KP",
    "russia": "RU", "soviet union": "RU", "czech republic": "CZ", "czechia": "CZ",
    "the netherlands": "NL", "holland": "NL", "ivory coast": "CI", "vietnam": "VN",
    "taiwan": "TW", "iran": "IR", "syria": "SY", "laos": "LA", "bolivia": "BO",
    "venezuela": "VE", "tanzania": "TZ", "moldova": "MD", "macedonia": "MK",
    "north macedonia": "MK", "bosnia and herzegovina": "BA", "bosnia": "BA",
    "puerto rico": "PR", "hong kong": "HK",
}

US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia (u.s. state)", "hawaii", "idaho", "illinois", "indiana",
    "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts",
    "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming", "washington, d.c.", "d.c.",
}
CANADIAN_PROVINCES = {
    "ontario", "quebec", "british columbia", "alberta", "manitoba", "saskatchewan",
    "nova scotia", "new brunswick", "newfoundland and labrador", "prince edward island",
}


def _candidates(origin: str) -> list[str]:
    """Place names in an origin, most specific country guess first."""
    origin = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", origin)
    parts = [part.strip(" .") for part in re.split(r",|\n", origin) if part.strip(" .")]
    return list(reversed(parts))


def resolve_country(origin: str) -> str | None:
    """
    The ISO code of the country in a Wikipedia origin ("London, England",
    "Los Angeles, California, U.S.", "Ljubljana, Slovenia"), or None.
    """
    if not origin or not origin.strip():
        return None
    countries = list_countries()
    by_name = {normalize(name): code for code, name in countries}

    for place in _candidates(origin):
        lower = place.lower().strip()
        if lower in ALIASES:
            return ALIASES[lower]
        if lower in US_STATES:
            return "US"
        if lower in CANADIAN_PROVINCES:
            return "CA"
        key = normalize(place)
        if key in by_name:
            return by_name[key]
        # "Korea" vs "Korea, Republic of" style names in the service
        if len(key) >= 4:
            for name_key, code in by_name.items():
                if name_key.startswith(key):
                    return code
    return None


def country_for_origin(origin: str | None) -> CountryInfo | None:
    """Country details for a Wikipedia origin, or None if it can't be placed."""
    code = resolve_country(origin or "")
    return country_info(code) if code else None


def clear_cache() -> None:
    _cache.clear()
    persistent_cache.store().clear("countryinfo")
