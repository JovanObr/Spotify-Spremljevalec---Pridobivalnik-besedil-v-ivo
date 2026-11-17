import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from services import ai_service, lyrics_service, musicatlas_service
from utils import persistent_cache
from utils.persistent_cache import MISSING, PersistentCache


class TempCacheTestCase(unittest.TestCase):
    """Each test gets its own cache file, removed afterwards."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "sub", "cache.sqlite3")
        persistent_cache.configure(self.path)
        self.addCleanup(persistent_cache.configure, None)
        self.addCleanup(self.dir.cleanup)

    def restart(self):
        """Like restarting the app: memory caches are empty, the file stays."""
        persistent_cache.configure(self.path)
        lyrics_service.clear_cache()
        ai_service.clear_cache()
        musicatlas_service.clear_cache()


class TestPersistentCache(TempCacheTestCase):

    def test_round_trip_and_survives_reopening(self):
        persistent_cache.store().set("ns", ["a", 1], {"x": [1, 2]}, 60)
        self.restart()

        self.assertEqual(persistent_cache.store().get("ns", ["a", 1]), {"x": [1, 2]})
        self.assertIs(persistent_cache.store().get("other", ["a", 1]), MISSING)

    def test_none_is_a_value(self):
        persistent_cache.store().set("ns", "k", None, 60)
        self.assertIsNone(persistent_cache.store().get("ns", "k"))

    def test_expired_entries_are_missing(self):
        cache = PersistentCache(":memory:")
        cache.set("ns", "k", 1, ttl_seconds=-1)
        self.assertIs(cache.get("ns", "k"), MISSING)

    def test_remember_computes_once(self):
        compute = MagicMock(return_value=(1, 2))

        first = persistent_cache.remember("ns", "k", 60, compute, encode=list, decode=tuple)
        second = persistent_cache.remember("ns", "k", 60, compute, encode=list, decode=tuple)

        self.assertEqual(first, second)
        self.assertEqual(second, (1, 2))
        compute.assert_called_once()

    def test_bad_stored_shape_is_recomputed(self):
        persistent_cache.store().set("ns", "k", "not a dict", 60)

        value = persistent_cache.remember("ns", "k", 60, lambda: {"ok": 1}, decode=lambda d: d["ok"] and d)

        self.assertEqual(value, {"ok": 1})

    def test_off_by_default(self):
        persistent_cache.configure(None)
        persistent_cache.store().set("ns", "k", 1, 60)
        self.assertIs(persistent_cache.store().get("ns", "k"), MISSING)

    def test_unusable_path_is_ignored(self):
        with tempfile.NamedTemporaryFile() as blocker:
            cache = PersistentCache(os.path.join(blocker.name, "cache.sqlite3"))  # parent is a file
            cache.set("ns", "k", 1, 60)
            self.assertIs(cache.get("ns", "k"), MISSING)


class TestServicesUseIt(TempCacheTestCase):

    def test_lyrics_survive_a_restart(self):
        found = lyrics_service.Lyrics(
            track_name="Song", artist_name="Artist", album_name=None, plain_lyrics="a\nb",
            synced_lyrics="[00:01.00]a\n[00:02.00]b", instrumental=False,
        )
        with patch.object(lyrics_service, "_lookup", return_value=(found, True)) as lookup:
            lyrics_service.get_lyrics("Artist", "Song", None, 200_000)
            self.restart()
            again = lyrics_service.get_lyrics("Artist", "Song", None, 200_000)

        lookup.assert_called_once()
        self.assertEqual([line.text for line in again.lines], ["a", "b"])
        self.assertEqual(again.lines[1].time_ms, 2000)

    def test_lyrics_not_found_is_remembered_too(self):
        with patch.object(lyrics_service, "_lookup", return_value=(None, True)) as lookup:
            lyrics_service.get_lyrics("Artist", "Nothing")
            self.restart()
            self.assertIsNone(lyrics_service.get_lyrics("Artist", "Nothing"))
        lookup.assert_called_once()

    def test_incomplete_lookups_are_not_stored(self):
        with patch.object(lyrics_service, "_lookup", return_value=(None, False)) as lookup:
            lyrics_service.get_lyrics("Artist", "Flaky")
            self.restart()
            lyrics_service.get_lyrics("Artist", "Flaky")
        self.assertEqual(lookup.call_count, 2)

    def test_ai_facts_and_meaning_survive_a_restart(self):
        answers = [
            ai_service.TrackFacts(facts=["One.", "Two."]),
            ai_service.SongMeaning(summary="About home.", themes=["home"]),
        ]
        with patch.object(ai_service, "is_configured", return_value=True), \
                patch.object(ai_service, "_ask", side_effect=answers) as ask:
            ai_service.generate_track_facts("Artist", "Song")
            ai_service.explain_song("Artist", "Song", lyrics="la la")
            self.restart()
            facts = ai_service.generate_track_facts("Artist", "Song")
            meaning = ai_service.explain_song("Artist", "Song", lyrics="la la")

        self.assertEqual(ask.call_count, 2)
        self.assertEqual(list(facts), ["One.", "Two."])
        self.assertEqual(meaning.themes, ["home"])

    def test_musicatlas_survives_a_restart(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "matches": [{"artist": "B", "title": "T", "platform_ids": {"spotify": "id1"}}],
            "hashtags": ["#indie"],
        }
        with patch.object(musicatlas_service, "get_musicatlas_api_key", return_value="key"), \
                patch.object(musicatlas_service._session, "post", return_value=response) as post:
            musicatlas_service.similar_tracks("A", "Song")
            self.restart()
            result = musicatlas_service.similar_tracks("A", "Song")

        post.assert_called_once()
        self.assertEqual(result.matches[0].spotify_id, "id1")
        self.assertEqual(result.tags, ["indie"])


if __name__ == "__main__":
    unittest.main()
