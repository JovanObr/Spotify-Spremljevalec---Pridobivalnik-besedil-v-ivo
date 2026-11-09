import unittest
from unittest.mock import MagicMock, patch

from services import recommendation_service
from services.ai_service import SongSuggestion
from services.recommendation_service import find_on_spotify, get_recommendations


def spotify_track(tid, name, artist):
    return {
        "id": tid,
        "type": "track",
        "uri": f"spotify:track:{tid}",
        "name": name,
        "duration_ms": 1000,
        "artists": [{"name": artist}],
        "album": {"name": "Album", "images": [{"url": "big"}, {"url": "small"}]},
    }


class FakeSpotify:
    """Search that knows a fixed catalog; matches loosely like Spotify does."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.queries = []

    def search(self, q, type, limit, market):
        self.queries.append(q)
        words = q.lower().replace('"', " ").replace("track:", " ").replace("artist:", " ").split()
        hits = [
            t for t in self.catalog
            if any(w in (t["name"] + " " + t["artists"][0]["name"]).lower() for w in words)
        ]
        return {"tracks": {"items": hits[:limit]}}


CATALOG = [
    spotify_track("a", "Harbour Lights", "The Low Tides"),
    spotify_track("b", "Night Platform", "Lena Varga"),
    spotify_track("c", "Copper Sky - Remastered 2011", "Mira Okafor"),
    spotify_track("d", "Static Bloom", "Lena Varga"),
]


class TestFindOnSpotify(unittest.TestCase):

    def test_finds_with_loose_artist_and_title(self):
        spotify = FakeSpotify(CATALOG)

        self.assertEqual(find_on_spotify(spotify, "Harbour Lights", "Low Tides").uri, "spotify:track:a")
        self.assertEqual(find_on_spotify(spotify, "Copper Sky", "Mira Okafor").uri, "spotify:track:c")

    def test_rejects_wrong_artist(self):
        spotify = FakeSpotify(CATALOG)

        self.assertIsNone(find_on_spotify(spotify, "Harbour Lights", "Someone Else"))

    def test_made_up_song_is_not_found(self):
        spotify = FakeSpotify(CATALOG)

        self.assertIsNone(find_on_spotify(spotify, "Imaginary Song", "Lena Varga"))
        self.assertEqual(len(spotify.queries), 2)  # precise, then forgiving


class TestGetRecommendations(unittest.TestCase):

    def setUp(self):
        recommendation_service.clear_cache()
        self.spotify = FakeSpotify(CATALOG)
        self.suggest = patch.object(
            recommendation_service.ai_service, "suggest_similar_songs"
        ).start()
        self.addCleanup(patch.stopall)

    def suggestions(self, *pairs):
        return [SongSuggestion(title=t, artist=a, reason=f"Because {t}") for t, a in pairs]

    def test_keeps_only_real_songs_and_skips_current(self):
        self.suggest.return_value = self.suggestions(
            ("Static Bloom", "Lena Varga"),        # the current song
            ("Imaginary Song", "Nobody"),          # made up
            ("Harbour Lights", "The Low Tides"),
            ("Night Platform", "Lena Varga"),
            ("Copper Sky", "Mira Okafor"),
        )

        recs = get_recommendations(
            self.spotify, "Lena Varga", "Static Bloom", None, "spotify:track:d"
        )

        self.assertEqual([r.track.uri for r in recs],
                         ["spotify:track:a", "spotify:track:b", "spotify:track:c"])
        self.assertEqual(recs[0].reason, "Because Harbour Lights")

    def test_at_most_three_and_no_duplicates(self):
        self.suggest.return_value = self.suggestions(
            ("Harbour Lights", "The Low Tides"),
            ("Harbour Lights", "Low Tides"),
            ("Night Platform", "Lena Varga"),
            ("Copper Sky", "Mira Okafor"),
            ("Static Bloom", "Lena Varga"),
        )

        recs = get_recommendations(self.spotify, "Other", "Song")

        self.assertEqual(len(recs), 3)
        self.assertEqual(len({r.track.uri for r in recs}), 3)

    def test_results_are_cached(self):
        self.suggest.return_value = self.suggestions(("Harbour Lights", "The Low Tides"))

        get_recommendations(self.spotify, "Other", "Song")
        get_recommendations(self.spotify, "Other", "Song")

        self.assertEqual(self.suggest.call_count, 1)

    def test_ai_errors_propagate_and_are_not_cached(self):
        from services.ai_service import AIServiceError
        self.suggest.side_effect = [AIServiceError("down"), self.suggestions(("Harbour Lights", "The Low Tides"))]

        with self.assertRaises(AIServiceError):
            get_recommendations(self.spotify, "Other", "Song")

        self.assertEqual(len(get_recommendations(self.spotify, "Other", "Song")), 1)


if __name__ == "__main__":
    unittest.main()
