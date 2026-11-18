"""The web-scraping, SOAP and PC-Axis sources, with saved responses (no network)."""

import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app import app
from services import country_service, source_registry, stats_service, wikipedia_service
from utils import pcaxis, persistent_cache


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def html_response(name: str, status: int = 200):
    response = MagicMock(status_code=status)
    response.text = fixture(name).decode("utf-8")
    return response


class FakeWikipedia:
    """Answers like en.wikipedia.org for the fixture pages."""

    PAGES = {
        "/wiki/Bohemian_Rhapsody_(film)": "wiki_film.html",
        "/wiki/Bohemian_Rhapsody": "wiki_song.html",
        "/wiki/Queen_(band)": "wiki_band.html",
    }

    def __init__(self):
        self.urls = []

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        if params and params.get("title") == "Special:Search":
            return html_response("wiki_search.html")
        for path, name in self.PAGES.items():
            if url.endswith(path):
                return html_response(name)
        return html_response("wiki_film.html", status=404)


class TestWikipediaScraping(unittest.TestCase):

    def setUp(self):
        persistent_cache.configure(None)
        wikipedia_service.clear_cache()
        source_registry.reset()
        self.fake = FakeWikipedia()
        patcher = patch.object(wikipedia_service._session, "get", side_effect=self.fake.get)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_finds_the_song_and_follows_its_artist_link(self):
        details = wikipedia_service.get_details("Queen", "Bohemian Rhapsody - Remastered 2011")

        song = details.song
        self.assertEqual(song.title, "Bohemian Rhapsody")
        self.assertEqual(song.album, "A Night at the Opera")
        fields = {f.label: f.values for f in song.fields}
        self.assertEqual(fields["Released"], ["31 October 1975"])  # footnote [1] removed
        self.assertEqual(fields["Genre"], ["Progressive rock", "hard rock"])
        self.assertEqual(fields["Label"], ["EMI", "Elektra"])  # split on <br>
        self.assertNotIn("B-side", fields)

        self.assertEqual(details.artist.name, "Queen")
        self.assertEqual(details.artist.origin, "London, England")
        self.assertTrue(details.artist.summary.startswith("Queen are a British rock band"))
        # The film result was skipped; the artist came from the song's link, not a search
        self.assertTrue(any(url.endswith("/wiki/Queen_(band)") for url in self.fake.urls))

    def test_cached_after_the_first_time(self):
        wikipedia_service.get_details("Queen", "Bohemian Rhapsody")
        count = len(self.fake.urls)
        wikipedia_service.get_details("Queen", "Bohemian Rhapsody")
        self.assertEqual(len(self.fake.urls), count)

    def test_song_by_another_artist_is_rejected(self):
        details = wikipedia_service.get_details("ABBA", "Bohemian Rhapsody")
        self.assertIsNone(details.song)

    def test_person_born_in_a_place(self):
        from bs4 import BeautifulSoup

        artist = wikipedia_service.parse_artist(
            BeautifulSoup(fixture("wiki_person.html"), "html.parser"), "u"
        )

        self.assertEqual(artist.origin, "Los Angeles, California, U.S.")
        self.assertIn("is an American singer-songwriter", artist.summary)
        self.assertNotIn("born", artist.summary)

    def test_network_failure_is_reported(self):
        import requests

        with patch.object(wikipedia_service._session, "get", side_effect=requests.ConnectionError("down")):
            with self.assertRaises(wikipedia_service.WikipediaError):
                wikipedia_service.get_details("Queen", "Something else")
        self.assertEqual(
            next(s for s in source_registry.describe() if s["id"] == "wikipedia")["state"], "error"
        )


def soap_response(name: str, status: int = 200):
    response = MagicMock(status_code=status)
    response.content = fixture(name)
    return response


class TestCountrySoap(unittest.TestCase):

    def setUp(self):
        persistent_cache.configure(None)
        country_service.clear_cache()
        self.posts = []

        def post(url, data, headers, timeout):
            self.posts.append(data.decode("utf-8"))
            if b"ListOfCountryNamesByName" in data:
                return soap_response("soap_country_list.xml")
            return soap_response("soap_full_info.xml")

        patcher = patch.object(country_service._session, "post", side_effect=post)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_envelope(self):
        xml = country_service.envelope("FullCountryInfo", {"sCountryISOCode": "SI"})
        self.assertIn('<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">', xml)
        self.assertIn('<FullCountryInfo xmlns="http://www.oorsprong.org/websamples.countryinfo">'
                      "<sCountryISOCode>SI</sCountryISOCode></FullCountryInfo>", xml)

    def test_origins_to_countries(self):
        cases = {
            "London, England": "GB",
            "Los Angeles, California, U.S.": "US",
            "Ljubljana, Slovenia": "SI",
            "Toronto, Ontario": "CA",
            "Stockholm, Sweden[1]": "SE",
            "Somewhere": None,
        }
        for origin, code in cases.items():
            with self.subTest(origin=origin):
                self.assertEqual(country_service.resolve_country(origin), code)
        # The country list is fetched once
        self.assertEqual(sum("ListOfCountryNamesByName" in p for p in self.posts), 1)

    def test_full_country_info(self):
        info = country_service.country_for_origin("London, England")

        self.assertEqual(info.name, "United Kingdom")
        self.assertEqual(info.capital, "London")
        self.assertEqual(info.currency, "GBP")
        self.assertEqual(info.languages, ["English"])
        self.assertTrue(info.flag_url.endswith("United_Kingdom.jpg"))
        self.assertIn("<sCountryISOCode>GB</sCountryISOCode>", self.posts[-1])

    def test_soap_fault(self):
        with patch.object(country_service._session, "post", return_value=soap_response("soap_fault.xml", 500)):
            with self.assertRaises(country_service.CountryServiceError) as caught:
                country_service.country_info("FR")
        self.assertIn("Operation not supported", str(caught.exception))

    def test_bad_code(self):
        with self.assertRaises(ValueError):
            country_service.country_info("Slovenia")


class TestPcAxis(unittest.TestCase):

    def test_parse_fixture(self):
        table = pcaxis.parse(fixture("sistat_concerts.px"))

        self.assertEqual(table.title, "Concerts and attendance by type of music, Slovenia")
        self.assertEqual([name for name, _ in table.dimensions], ["TYPE OF MUSIC", "YEAR", "MEASURES"])
        self.assertEqual(table.value(**{"TYPE OF MUSIC": "Rock", "YEAR": "2023", "MEASURES": "Attendance"}), 95000)
        self.assertIsNone(table.value(**{"TYPE OF MUSIC": "Popular music", "YEAR": "2024", "MEASURES": "Attendance"}))
        self.assertEqual(table.last_updated, "20250601 10:00")
        self.assertEqual(table.notes, ["Concerts held at the institutions' own venues."])

    def test_wrong_number_of_cells(self):
        broken = fixture("sistat_concerts.px").replace(b"400 90000", b"400")
        with self.assertRaises(pcaxis.PxError):
            pcaxis.parse(broken)

    def test_windows_1250(self):
        text = 'CODEPAGE="windows-1250";\nSTUB="ZVRST";\nVALUES("ZVRST")="Zborovska glasba","Narodno-zabavna";\nHEADING="LETO";\nVALUES("LETO")="2024";\nTITLE="Koncerti po zvrsti, Slovenija (število)";\nDATA=\n1 2;\n'
        table = pcaxis.parse(text.encode("windows-1250"))
        self.assertIn("število", table.title)


class TestStatsService(unittest.TestCase):

    def setUp(self):
        persistent_cache.configure(None)
        stats_service._memory = None
        patcher = patch.dict("os.environ", {"SISTAT_TABLE": "Culture/0001.px"})
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch.object(stats_service, "download", return_value=fixture("sistat_concerts.px"))
    def test_json_shape_and_daily_refresh(self, download):
        data = stats_service.get_stats()

        self.assertEqual(data["time_dimension"], "YEAR")
        self.assertEqual(data["dimensions"][0]["values"], ["Choral and vocal", "Popular music", "Rock"])
        self.assertIn([2, 1, 1, 95000.0], data["observations"])
        self.assertFalse(data["stale"])

        stats_service.get_stats()
        self.assertEqual(download.call_count, 1)  # within 24 hours

        stats_service._memory["fetched_at"] = time.time() - 25 * 3600
        stats_service.get_stats()
        self.assertEqual(download.call_count, 2)

    def test_last_copy_when_sistat_is_down(self):
        with patch.object(stats_service, "download", return_value=fixture("sistat_concerts.px")):
            stats_service.get_stats()
        stats_service.clear_cache()

        with patch.object(stats_service, "download", side_effect=stats_service.StatsError("down")):
            data = stats_service.get_stats()

        self.assertTrue(data["stale"])
        self.assertEqual(data["error"], "down")

    def test_not_configured(self):
        with patch.dict("os.environ", {"SISTAT_TABLE": ""}), patch.object(stats_service, "DEFAULT_TABLE", ""):
            with self.assertRaises(stats_service.StatsNotConfigured):
                stats_service.get_stats()

    def test_query_asks_for_everything_as_px(self):
        query = stats_service._post_query({"variables": [{"code": "LETO", "values": ["2024"]}]})
        self.assertEqual(query["response"], {"format": "px"})
        self.assertEqual(query["query"][0]["selection"], {"filter": "all", "values": ["*"]})


class TestRoutes(unittest.TestCase):

    def setUp(self):
        persistent_cache.configure(None)
        source_registry.reset()
        self.client = TestClient(app)

    def test_details_with_country(self):
        details = wikipedia_service.Details(
            song=None,
            artist=wikipedia_service.ArtistDetails(name="Queen", url="u", origin="London, England"),
        )
        info = country_service.CountryInfo("GB", "United Kingdom", "London", "44", "EU", "GBP", None, ["English"])
        with patch.object(wikipedia_service, "get_details", return_value=details), \
                patch.object(country_service, "country_for_origin", return_value=info):
            data = self.client.get("/api/details", params={"artist": "Queen", "title": "X"}).json()

        self.assertIsNone(data["song"])
        self.assertEqual(data["artist"]["origin"], "London, England")
        self.assertEqual(data["country"]["capital"], "London")
        self.assertEqual(data["errors"], {})

    def test_details_when_soap_is_down(self):
        details = wikipedia_service.Details(
            song=None, artist=wikipedia_service.ArtistDetails(name="Queen", url="u", origin="London")
        )
        with patch.object(wikipedia_service, "get_details", return_value=details), \
                patch.object(country_service, "country_for_origin",
                             side_effect=country_service.CountryServiceError("down")):
            data = self.client.get("/api/details", params={"artist": "Queen", "title": "X"}).json()

        self.assertIsNone(data["country"])
        self.assertEqual(data["errors"], {"country": "down"})

    def test_details_when_wikipedia_is_down(self):
        with patch.object(wikipedia_service, "get_details",
                          side_effect=wikipedia_service.WikipediaError("down")):
            response = self.client.get("/api/details", params={"artist": "Queen", "title": "X"})
        self.assertEqual(response.status_code, 502)

    def test_stats_not_configured(self):
        with patch.object(stats_service, "get_stats", side_effect=stats_service.StatsNotConfigured("no")):
            self.assertEqual(self.client.get("/api/stats").status_code, 503)

    def test_sources_list(self):
        source_registry.record_success("wikipedia")

        data = self.client.get("/api/sources").json()

        technologies = {s["technology"] for s in data["sources"]}
        self.assertTrue({"REST", "SOAP", "Web scraping", "PC-Axis"} <= technologies)
        self.assertEqual([d["technology"] for d in data["delivery"]], ["REST", "gRPC"])
        wikipedia = next(s for s in data["sources"] if s["id"] == "wikipedia")
        self.assertEqual(wikipedia["state"], "ok")
        self.assertIsNotNone(wikipedia["last_success"])

    def test_refresh(self):
        with patch.object(wikipedia_service, "clear_cache") as clear:
            response = self.client.post("/api/sources/wikipedia/refresh")
        self.assertEqual(response.json(), {"refreshed": "wikipedia"})
        clear.assert_called_once()

    def test_quota_sources_cannot_be_refreshed(self):
        self.assertEqual(self.client.post("/api/sources/gemini/refresh").status_code, 409)
        self.assertEqual(self.client.post("/api/sources/nope/refresh").status_code, 404)


class TestRegistry(unittest.TestCase):

    def setUp(self):
        persistent_cache.configure(None)
        source_registry.reset()

    def test_tracking(self):
        with source_registry.tracking("lrclib"):
            pass
        with self.assertRaises(RuntimeError):
            with source_registry.tracking("lrclib"):
                raise RuntimeError("boom")

        lrclib = next(s for s in source_registry.describe() if s["id"] == "lrclib")
        self.assertEqual(lrclib["state"], "error")
        self.assertEqual(lrclib["last_error"], "boom")
        self.assertEqual(lrclib["requests_this_run"], 2)

    def test_unused(self):
        self.assertEqual({s["state"] for s in source_registry.describe()}, {"unused"})


if __name__ == "__main__":
    unittest.main()
