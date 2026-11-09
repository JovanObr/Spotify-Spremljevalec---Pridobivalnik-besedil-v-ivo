import unittest
from unittest.mock import MagicMock

from services.spotify_service import (
    SPOTIFY_SCOPE,
    add_to_queue,
    control_playback,
    play_track,
    seek,
)


class TestControlPlayback(unittest.TestCase):

    def test_actions_call_matching_spotify_methods(self):
        spotify = MagicMock()

        for action, method in [
            ("play", spotify.start_playback),
            ("pause", spotify.pause_playback),
            ("next", spotify.next_track),
            ("previous", spotify.previous_track),
        ]:
            control_playback(spotify, action)
            method.assert_called_once_with()

    def test_unknown_action_raises_value_error(self):
        with self.assertRaises(ValueError):
            control_playback(MagicMock(), "shuffle")

    def test_scope_includes_permissions_for_planned_features(self):
        scopes = SPOTIFY_SCOPE.split()

        for scope in (
            "user-read-currently-playing",
            "user-modify-playback-state",
            "playlist-read-private",
            "streaming",
        ):
            self.assertIn(scope, scopes)

        self.assertEqual(len(scopes), len(set(scopes)))

    def test_seek(self):
        spotify = MagicMock()

        seek(spotify, 42000)

        spotify.seek_track.assert_called_once_with(42000)

    def test_seek_rejects_negative_position(self):
        with self.assertRaises(ValueError):
            seek(MagicMock(), -1)


    def test_play_track(self):
        spotify = MagicMock()

        play_track(spotify, "spotify:track:x")

        spotify.start_playback.assert_called_once_with(device_id=None, uris=["spotify:track:x"])

    def test_add_to_queue(self):
        spotify = MagicMock()

        add_to_queue(spotify, "spotify:track:x")

        spotify.add_to_queue.assert_called_once_with("spotify:track:x")


if __name__ == "__main__":
    unittest.main()
