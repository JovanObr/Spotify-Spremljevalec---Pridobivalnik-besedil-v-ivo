import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from models.track import Playback
from services import prefetch_service
from services.prefetch_service import Prefetcher, next_in_queue
from utils.single_flight import SingleFlight


class ImmediateExecutor:
    """Runs submitted work right away, so tests are deterministic."""

    def submit(self, fn, *args):
        fn(*args)


def make_item(tid, title="Song", artists=("Artist A", "Artist B")):
    return {
        "id": tid,
        "type": "track",
        "uri": f"spotify:track:{tid}",
        "name": title,
        "duration_ms": 200000,
        "artists": [{"name": name} for name in artists],
        "album": {"name": "Album", "images": []},
    }


def make_playback(tid="t1"):
    return Playback.from_spotify({"is_playing": True, "progress_ms": 0, "item": make_item(tid)})


class TestPrefetcher(unittest.TestCase):

    def setUp(self):
        self.spotify = MagicMock()
        self.spotify.queue.return_value = {
            "queue": [{"type": "episode"}, make_item("t2", "Next Song")]
        }
        self.prefetcher = Prefetcher(executor=ImmediateExecutor())

        patches = [
            patch.object(prefetch_service.lyrics_service, "get_lyrics"),
            patch.object(prefetch_service.ai_service, "generate_track_facts"),
            patch.object(prefetch_service.recommendation_service, "get_recommendations"),
            patch.object(prefetch_service.recommendation_service, "is_available", return_value=True),
            patch.object(prefetch_service.ai_service, "is_configured", return_value=True),
            patch.object(prefetch_service, "is_prefetch_enabled", return_value=True),
        ]
        self.lyrics, self.facts, self.recs, self.recs_available, _, self.enabled = [
            p.start() for p in patches
        ]
        for p in patches:
            self.addCleanup(p.stop)

    def test_new_song_warms_current_and_next(self):
        self.prefetcher.on_playback(self.spotify, make_playback("t1"))

        titles = [call.args[1] for call in self.lyrics.call_args_list]
        self.assertEqual(titles, ["Song", "Next Song"])
        self.assertEqual(self.facts.call_count, 2)
        self.recs.assert_any_call(
            self.spotify, "Artist A", "Next Song", "Album", "spotify:track:t2"
        )

    def test_uses_same_arguments_as_frontend(self):
        self.prefetcher.on_playback(self.spotify, make_playback("t1"))

        # Frontend: first artist, title, album, duration_ms
        self.lyrics.assert_any_call("Artist A", "Song", "Album", 200000)
        self.facts.assert_any_call("Artist A", "Song", "Album")

    def test_same_song_is_not_prefetched_again(self):
        self.prefetcher.on_playback(self.spotify, make_playback("t1"))
        self.prefetcher.on_playback(self.spotify, make_playback("t1"))

        self.assertEqual(self.spotify.queue.call_count, 1)

    def test_disabled(self):
        self.enabled.return_value = False

        self.prefetcher.on_playback(self.spotify, make_playback("t1"))

        self.lyrics.assert_not_called()

    def test_no_ai_without_api_key(self):
        self.recs_available.return_value = False
        with patch.object(prefetch_service.ai_service, "is_configured", return_value=False):
            self.prefetcher.on_playback(self.spotify, make_playback("t1"))

        self.facts.assert_not_called()
        self.recs.assert_not_called()
        self.assertEqual(self.lyrics.call_count, 2)

    def test_errors_are_ignored(self):
        self.lyrics.side_effect = RuntimeError("boom")
        self.spotify.queue.side_effect = RuntimeError("no device")

        self.prefetcher.on_playback(self.spotify, make_playback("t1"))  # no raise

        self.assertEqual(self.facts.call_count, 1)

    def test_next_in_queue_skips_non_tracks(self):
        track = next_in_queue(self.spotify)

        self.assertEqual(track.title, "Next Song")


class TestSingleFlight(unittest.TestCase):

    def test_second_caller_waits_for_first(self):
        flight = SingleFlight()
        calls = []
        cache = {}

        def work():
            with flight.lock("song"):
                if "song" in cache:
                    return
                calls.append(1)
                time.sleep(0.05)
                cache["song"] = "facts"

        threads = [threading.Thread(target=work) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(calls), 1)
        self.assertEqual(flight._locks, {})  # cleaned up


if __name__ == "__main__":
    unittest.main()
