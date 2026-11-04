import unittest
from unittest.mock import patch

from main import process_playback


class TestPlaybackMonitor(unittest.TestCase):

    def setUp(self):
        self.track_a = {
            "id": "track_a",
            "type": "track",
            "name": "Song A",
            "artists": [{"name": "Artist A"}],
            "album": {"name": "Album A"},
            "duration_ms": 200000,
        }

        self.track_b = {
            "id": "track_b",
            "type": "track",
            "name": "Song B",
            "artists": [{"name": "Artist B"}],
            "album": {"name": "Album B"},
            "duration_ms": 180000,
        }

    def make_playback(self, track, is_playing=True):
        return {
            "item": track,
            "is_playing": is_playing,
            "progress_ms": 30000,
        }

    @patch("main.display_track")
    def test_new_track_is_displayed(self, mock_display):
        result = process_playback(
            self.make_playback(self.track_a),
            None,
            None,
            False,
        )

        self.assertEqual(result, ("track_a", True, False))
        mock_display.assert_called_once()

    @patch("main.display_track")
    def test_same_track_is_not_displayed_again(self, mock_display):
        result = process_playback(
            self.make_playback(self.track_a),
            "track_a",
            True,
            False,
        )

        self.assertEqual(result, ("track_a", True, False))
        mock_display.assert_not_called()

    @patch("main.display_track")
    def test_different_track_is_displayed(self, mock_display):
        result = process_playback(
            self.make_playback(self.track_b),
            "track_a",
            True,
            False,
        )

        self.assertEqual(result, ("track_b", True, False))
        mock_display.assert_called_once()

    @patch("main.display_track")
    def test_paused_track_updates_playback_state(self, mock_display):
        result = process_playback(
            self.make_playback(self.track_a, False),
            "track_a",
            True,
            False,
        )

        self.assertEqual(result, ("track_a", False, False))
        mock_display.assert_not_called()

    @patch("main.display_track")
    def test_resuming_same_track_does_not_redisplay_track(self, mock_display):
        result = process_playback(
            self.make_playback(self.track_a, True),
            "track_a",
            False,
            False,
        )

        self.assertEqual(result, ("track_a", True, False))
        mock_display.assert_not_called()

    @patch("main.display_track")
    def test_new_track_after_empty_playback_is_displayed(self, mock_display):
        result = process_playback(
            self.make_playback(self.track_b),
            None,
            None,
            True,
        )

        self.assertEqual(result, ("track_b", True, False))
        mock_display.assert_called_once()

    def test_no_playback_resets_state(self):
        result = process_playback(
            None,
            "track_a",
            True,
            False,
        )

        self.assertEqual(result, (None, None, True))

    def test_empty_playback_does_not_repeat_message(self):
        result = process_playback(
            None,
            None,
            None,
            True,
        )

        self.assertEqual(result, (None, None, True))

    def test_non_track_content_resets_state(self):
        playback = {
            "item": {
                "id": "episode_a",
                "type": "episode",
            },
            "is_playing": True,
        }

        result = process_playback(
            playback,
            "track_a",
            True,
            False,
        )

        self.assertEqual(result, (None, None, True))


if __name__ == "__main__":
    unittest.main()