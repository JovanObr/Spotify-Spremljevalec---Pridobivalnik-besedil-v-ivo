import unittest
from unittest.mock import MagicMock, patch

from services import musicatlas_service, recommendation_service
from services.ai_service import AINotConfiguredError, SongSuggestion
from services.musicatlas_service import MusicAtlasError, SimilarTrack, SimilarTracks
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
        patch.object(recommendation_service.ai_service, "is_configured", return_value=True).start()
        patch.object(musicatlas_service, "is_configured", return_value=False).start()
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

        result = get_recommendations(
            self.spotify, "Lena Varga", "Static Bloom", None, "spotify:track:d"
        )
        recs = result.items
        self.assertEqual(result.source, "ai")

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

        recs = get_recommendations(self.spotify, "Other", "Song").items

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

        self.assertEqual(len(get_recommendations(self.spotify, "Other", "Song").items), 1)



class SpotifyById(FakeSpotify):
    def __init__(self, catalog, unplayable=()):
        super().__init__(catalog)
        self.by_id = {t["id"]: t for t in catalog}
        self.unplayable = set(unplayable)
        self.track_calls = []

    def track(self, track_id, market=None):
        self.track_calls.append(track_id)
        item = self.by_id.get(track_id)
        if item and track_id in self.unplayable:
            return {**item, "is_playable": False}
        return item


class TestMusicAtlasRecommendations(unittest.TestCase):

    def setUp(self):
        recommendation_service.clear_cache()
        self.spotify = SpotifyById(CATALOG + [spotify_track("e", "Echo Room", "The Low Tides")])
        patch.object(musicatlas_service, "is_configured", return_value=True).start()
        self.ai_on = patch.object(
            recommendation_service.ai_service, "is_configured", return_value=True
        ).start()
        self.similar = patch.object(musicatlas_service, "similar_tracks").start()
        self.explain = patch.object(
            recommendation_service.ai_service, "explain_recommendations",
            side_effect=lambda a, t, picks: [f"Why {p[1]}" for p in picks],
        ).start()
        self.suggest = patch.object(
            recommendation_service.ai_service, "suggest_similar_songs"
        ).start()
        self.addCleanup(patch.stopall)

    def atlas(self, *pairs, tags=("dreampop",)):
        return SimilarTracks(
            matches=[SimilarTrack(artist=a, title=t, spotify_id=i) for t, a, i in pairs],
            tags=list(tags),
        )

    def test_musicatlas_picks_with_ai_reasons(self):
        self.similar.return_value = self.atlas(
            ("Static Bloom", "Lena Varga", "d"),          # current song
            ("Harbour Lights", "The Low Tides", "a"),
            ("Echo Room", "The Low Tides", "e"),          # same artist again
            ("Night Platform", "Lena Varga", "b"),
            ("Copper Sky", "Mira Okafor", "c"),
            ("No Id", "Someone", None),
        )

        result = get_recommendations(self.spotify, "Lena Varga", "Static Bloom", None, "spotify:track:d")

        self.assertEqual(result.source, "musicatlas")
        self.assertEqual([r.track.uri for r in result.items],
                         ["spotify:track:a", "spotify:track:b", "spotify:track:c"])
        self.assertEqual(result.items[0].reason, "Why Harbour Lights")
        self.assertEqual(result.tags, ("dreampop",))
        self.suggest.assert_not_called()
        self.assertEqual(self.spotify.queries, [])  # no searching needed

    def test_unplayable_tracks_are_skipped(self):
        self.spotify.unplayable = {"a"}
        self.similar.return_value = self.atlas(
            ("Harbour Lights", "The Low Tides", "a"), ("Copper Sky", "Mira Okafor", "c"),
        )

        result = get_recommendations(self.spotify, "X", "Y")

        self.assertEqual([r.track.uri for r in result.items], ["spotify:track:c"])

    def test_reasons_are_optional(self):
        self.explain.side_effect = recommendation_service.ai_service.AIServiceError("quota")
        self.similar.return_value = self.atlas(("Copper Sky", "Mira Okafor", "c"))

        result = get_recommendations(self.spotify, "X", "Y")

        self.assertIsNone(result.items[0].reason)
        self.assertEqual(result.source, "musicatlas")

    def test_works_without_ai(self):
        self.ai_on.return_value = False
        self.similar.return_value = self.atlas(("Copper Sky", "Mira Okafor", "c"))

        result = get_recommendations(self.spotify, "X", "Y")

        self.assertEqual(result.items[0].reason, None)
        self.explain.assert_not_called()

    def test_falls_back_to_ai_when_not_in_catalog(self):
        self.similar.return_value = SimilarTracks(matches=[], tags=[], in_catalog=False)
        self.suggest.return_value = [SongSuggestion(title="Copper Sky", artist="Mira Okafor", reason="R")]

        result = get_recommendations(self.spotify, "X", "Y")

        self.assertEqual(result.source, "ai")
        self.assertEqual(result.items[0].reason, "R")

    def test_falls_back_to_ai_on_quota(self):
        self.similar.side_effect = MusicAtlasError("limit", 429)
        self.suggest.return_value = [SongSuggestion(title="Copper Sky", artist="Mira Okafor", reason="R")]

        self.assertEqual(get_recommendations(self.spotify, "X", "Y").source, "ai")

    def test_nothing_available(self):
        self.ai_on.return_value = False
        self.similar.side_effect = MusicAtlasError("limit", 429)

        with self.assertRaises(AINotConfiguredError):
            get_recommendations(self.spotify, "X", "Y")


class TestMusicAtlasClient(unittest.TestCase):

    def setUp(self):
        musicatlas_service.clear_cache()
        patch.object(musicatlas_service, "get_musicatlas_api_key", return_value="key").start()
        self.post = patch.object(musicatlas_service._session, "post").start()
        self.addCleanup(patch.stopall)

    def respond(self, status=200, body=None):
        response = MagicMock(status_code=status)
        response.json.return_value = body
        self.post.return_value = response

    def test_parses_matches_and_sends_auth(self):
        self.respond(body={
            "success": True,
            "matches": [
                {"artist": "A", "title": "One", "platform_ids": {"spotify": "4uLU6hMCjMI75M1A2tKUQC"}},
                {"artist": "B", "title": "Two", "platform_ids": {"spotify": "spotify:track:abc"}},
                {"artist": "C", "title": "Three", "platform_ids": {}},
            ],
            "hashtags": ["#dreampop", "#shoegaze"],
        })

        result = musicatlas_service.similar_tracks("Artist", "Song")

        self.assertEqual([m.spotify_id for m in result.matches],
                         ["4uLU6hMCjMI75M1A2tKUQC", "abc", None])
        self.assertEqual(result.tags, ["dreampop", "shoegaze"])
        kwargs = self.post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer key")
        self.assertEqual(kwargs["json"], {"artist": "Artist", "track": "Song"})
        self.assertTrue(self.post.call_args.args[0].endswith("/api/similar_tracks"))

    def test_not_in_catalog_is_cached(self):
        self.respond(body={"in_catalog": False, "suggest_add": True})

        first = musicatlas_service.similar_tracks("A", "B")
        musicatlas_service.similar_tracks("a", "b")

        self.assertFalse(first.in_catalog)
        self.assertEqual(self.post.call_count, 1)

    def test_errors(self):
        for status in (401, 403, 429, 500):
            musicatlas_service.clear_cache()
            self.respond(status=status, body={})
            with self.assertRaises(MusicAtlasError) as context:
                musicatlas_service.similar_tracks("A", "B")
            self.assertEqual(context.exception.status_code, status)

    def test_requires_key(self):
        with patch.object(musicatlas_service, "get_musicatlas_api_key", return_value=None):
            with self.assertRaises(MusicAtlasError):
                musicatlas_service.similar_tracks("A", "B")


if __name__ == "__main__":
    unittest.main()
