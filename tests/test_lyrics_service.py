
import unittest
from unittest.mock import Mock, patch

import requests

from services import lyrics_service
from services.lyrics_service import (
    Lyrics,
    LyricsRateLimitError,
    LyricLine,
    LyricsServiceError,
    clean_title,
    clear_cache,
    get_lyrics,
    normalize,
    parse_synced_lyrics,
)


class FakeHttp:
    """Answers _session.get calls by URL (and optionally params)."""

    def __init__(self):
        self.routes = []
        self.calls = []

    def on(self, url_part, payload=None, status=200, when=None, error=None):
        self.routes.append((url_part, when or {}, payload, status, error))

    def get(self, url, params=None, timeout=None):
        params = params or {}
        self.calls.append((url, params))
        for url_part, when, payload, status, error in self.routes:
            if url_part in url and all(params.get(k) == v for k, v in when.items()):
                if error:
                    raise error
                response = Mock(status_code=status, headers={})
                response.json.return_value = payload
                if status >= 400 and status not in (404, 429):
                    response.raise_for_status.side_effect = requests.HTTPError(str(status))
                return response
        return Mock(status_code=404, headers={})

    def patch(self):
        return patch("services.lyrics_service._session.get", side_effect=self.get)

    def urls(self):
        return [url for url, _ in self.calls]


class TestLyricsService(unittest.TestCase):

    def setUp(self):
        clear_cache()
        self.response_data = {
            "trackName": "Example Song",
            "artistName": "Example Artist",
            "albumName": "Example Album",
            "instrumental": False,
            "plainLyrics": "First original test line.\nSecond original test line.",
            "syncedLyrics": "[00:10.00] First original test line.",
        }

    @patch("services.lyrics_service._session.get")
    def test_retrieves_lyrics_successfully(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = self.response_data
        mock_get.return_value = response

        lyrics = get_lyrics(
            "Example Artist",
            "Example Song",
            "Example Album",
            240000,
        )

        self.assertIsInstance(lyrics, Lyrics)
        self.assertEqual(lyrics.track_name, "Example Song")
        self.assertEqual(lyrics.artist_name, "Example Artist")
        self.assertEqual(lyrics.album_name, "Example Album")
        self.assertIn("First original test line", lyrics.plain_lyrics)
        self.assertIsNotNone(lyrics.synced_lyrics)
        self.assertFalse(lyrics.instrumental)

        request_kwargs = mock_get.call_args.kwargs

        self.assertEqual(
            request_kwargs["params"]["duration"],
            240,
        )

    @patch("services.lyrics_service._session.get")
    def test_missing_lyrics_returns_none(self, mock_get):
        response = Mock()
        response.status_code = 404
        mock_get.return_value = response

        lyrics = get_lyrics("Example Artist", "Unknown Song")

        self.assertIsNone(lyrics)

    @patch("services.lyrics_service._session.get")
    def test_instrumental_track(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            **self.response_data,
            "instrumental": True,
            "plainLyrics": None,
            "syncedLyrics": None,
        }
        mock_get.return_value = response

        lyrics = get_lyrics("Example Artist", "Example Song")

        self.assertIsNotNone(lyrics)
        self.assertTrue(lyrics.instrumental)
        self.assertIsNone(lyrics.plain_lyrics)
        self.assertIsNone(lyrics.synced_lyrics)

    @patch("services.lyrics_service._session.get")
    def test_rate_limit_raises_specific_exception(self, mock_get):
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "30"}
        mock_get.return_value = response

        with self.assertRaises(LyricsRateLimitError) as context:
            get_lyrics("Example Artist", "Example Song")

        self.assertEqual(context.exception.retry_after, "30")

    @patch("services.lyrics_service._session.get")
    def test_network_error_raises_service_error(self, mock_get):
        mock_get.side_effect = requests.Timeout("Connection timed out")

        with self.assertRaises(LyricsServiceError):
            get_lyrics("Example Artist", "Example Song")

    @patch("services.lyrics_service._session.get")
    def test_server_error_raises_service_error(self, mock_get):
        response = Mock()
        response.status_code = 500
        response.raise_for_status.side_effect = requests.HTTPError(
            "Server error"
        )
        mock_get.return_value = response

        with self.assertRaises(LyricsServiceError):
            get_lyrics("Example Artist", "Example Song")

    def test_empty_artist_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_lyrics("", "Example Song")

    def test_empty_title_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_lyrics("Example Artist", "")

    def test_invalid_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_lyrics("Example Artist", "Example Song", duration_ms=0)

    def test_long_track_is_looked_up_without_duration(self):
        with patch("services.lyrics_service._session.get") as mock_get:
            response = Mock()
            response.status_code = 200
            response.json.return_value = self.response_data
            mock_get.return_value = response

            get_lyrics("Example Artist", "Example Song", duration_ms=4_000_000)

            self.assertNotIn("duration", mock_get.call_args.kwargs["params"])

    @patch("services.lyrics_service._session.get")
    def test_falls_back_to_search_when_exact_match_missing(self, mock_get):
        not_found = Mock(status_code=404)

        search = Mock(status_code=200)
        search.json.return_value = [
            {**self.response_data, "duration": 300, "syncedLyrics": None},
            {**self.response_data, "duration": 241},
            {**self.response_data, "duration": 239, "syncedLyrics": None},
        ]

        mock_get.side_effect = [not_found, search]

        lyrics = get_lyrics(
            "Example Artist",
            "Example Song - Remastered 2011",
            duration_ms=240000,
        )

        self.assertIsNotNone(lyrics.synced_lyrics)
        search_call = mock_get.call_args_list[1]
        self.assertTrue(search_call.args[0].endswith("/search"))
        self.assertEqual(
            search_call.kwargs["params"]["track_name"],
            "Example Song",
        )

    def test_search_ignores_results_with_wrong_duration(self):
        http = FakeHttp()
        http.on("/search", [{**self.response_data, "duration": 400}])

        with http.patch():
            lyrics = get_lyrics(
                "Example Artist", "Example Song", duration_ms=240000
            )

        self.assertIsNone(lyrics)

    @patch("services.lyrics_service._session.get")
    def test_results_are_cached(self, mock_get):
        response = Mock(status_code=200)
        response.json.return_value = self.response_data
        mock_get.return_value = response

        get_lyrics("Example Artist", "Example Song")
        get_lyrics("Example Artist", "Example Song")

        self.assertEqual(mock_get.call_count, 1)

    def test_synced_lyrics_are_parsed_into_lines(self):
        lyrics_lines = parse_synced_lyrics(
            "[ar:Example]\n"
            "[00:10.00] First line\n"
            "[00:05.5]Intro\n"
            "[01:02.345][01:30.00] Chorus\n"
            "[00:20.00]\n"
        )

        self.assertEqual(
            lyrics_lines,
            [
                LyricLine(5500, "Intro"),
                LyricLine(10000, "First line"),
                LyricLine(20000, ""),
                LyricLine(62345, "Chorus"),
                LyricLine(90000, "Chorus"),
            ],
        )

    def test_clean_title_removes_spotify_suffixes(self):
        self.assertEqual(clean_title("Song - Remastered 2011"), "Song")
        self.assertEqual(clean_title("Song (feat. Someone)"), "Song")
        self.assertEqual(clean_title("Song [Radio Edit]"), "Song")
        self.assertEqual(clean_title("Anti-Hero"), "Anti-Hero")
        self.assertEqual(clean_title("(I Can't Get No) Satisfaction"),
                         "(I Can't Get No) Satisfaction")



class TestLyricsSources(unittest.TestCase):
    """Search strategies and the backup source."""

    def setUp(self):
        clear_cache()
        self.synced = {
            "trackName": "Niche Song",
            "artistName": "Ivo Petrič",
            "instrumental": False,
            "plainLyrics": "Line",
            "syncedLyrics": "[00:01.00]Line",
            "duration": 200,
        }
        self.plain_only = {**self.synced, "syncedLyrics": None}

    def lookup(self, http, **kwargs):
        args = {"artist": "Ivo Petric", "title": "Niche Song", "duration_ms": 200000}
        args.update(kwargs)
        with http.patch():
            return get_lyrics(**args)

    def test_exact_match_without_album_is_tried(self):
        http = FakeHttp()
        http.on("/get", self.synced, when={"track_name": "Niche Song"})
        http.routes.insert(0, ("/get", {"album_name": "Deluxe"}, None, 404, None))

        lyrics = self.lookup(http, album="Deluxe")

        self.assertIsNotNone(lyrics.synced_lyrics)
        self.assertEqual(len(http.calls), 2)
        self.assertNotIn("album_name", http.calls[1][1])

    def test_plain_match_keeps_looking_for_synced(self):
        http = FakeHttp()
        http.on("/get", self.plain_only)
        http.on("/search", [self.synced], when={"track_name": "Niche Song"})

        lyrics = self.lookup(http)

        self.assertIsNotNone(lyrics.synced_lyrics)

    def test_plain_match_is_used_when_nothing_better(self):
        http = FakeHttp()
        http.on("/get", self.plain_only)

        lyrics = self.lookup(http)

        self.assertEqual(lyrics.plain_lyrics, "Line")
        self.assertEqual(lyrics.source, "LRCLIB")
        self.assertFalse(any("lyrics.ovh" in url for url in http.urls()))

    def test_free_text_search_matches_artist_spelling(self):
        http = FakeHttp()
        http.on("/search", [self.synced], when={"q": "Ivo Petric Niche Song"})

        lyrics = self.lookup(http)

        self.assertEqual(lyrics.artist_name, "Ivo Petrič")

    def test_title_only_search_rejects_other_artists(self):
        http = FakeHttp()
        http.on("/search", [{**self.synced, "artistName": "Someone Else"}],
                when={"q": "Niche Song"})

        self.assertIsNone(self.lookup(http))

    def test_lyrics_ovh_backup(self):
        http = FakeHttp()
        http.on("api.lyrics.ovh", {
            "lyrics": "Paroles de la chanson Niche Song par Ivo\r\nFirst\r\n\r\n\r\nSecond"
        })

        lyrics = self.lookup(http, title="Niche Song - Live")

        self.assertEqual(lyrics.source, "lyrics.ovh")
        self.assertEqual(lyrics.plain_lyrics, "First\n\nSecond")
        self.assertEqual(lyrics.lines, [])
        self.assertTrue(http.urls()[-1].endswith("/Ivo%20Petric/Niche%20Song"))

    def test_lrclib_failure_falls_back_but_is_not_cached(self):
        http = FakeHttp()
        http.on("lrclib.net", error=requests.Timeout("down"))
        http.on("api.lyrics.ovh", {"lyrics": "Backup"})

        first = self.lookup(http)
        calls = len(http.calls)
        self.lookup(http)

        self.assertEqual(first.source, "lyrics.ovh")
        self.assertGreater(len(http.calls), calls)  # asked again: not cached

    def test_providers_can_be_configured(self):
        http = FakeHttp()

        with patch.dict("os.environ", {"LYRICS_PROVIDERS": "lyricsovh"}):
            self.lookup(http)

        self.assertTrue(all("lyrics.ovh" in url for url in http.urls()))

    def test_no_lyrics_anywhere_is_cached(self):
        http = FakeHttp()

        self.assertIsNone(self.lookup(http))
        calls = len(http.calls)
        self.assertIsNone(self.lookup(http))
        self.assertEqual(len(http.calls), calls)

    def test_normalize(self):
        self.assertEqual(normalize("Ivo Petrič & The Band"), "ivopetricandband")
        self.assertEqual(normalize("The Low Tides"), normalize("Low Tides"))


if __name__ == "__main__":
    unittest.main()
