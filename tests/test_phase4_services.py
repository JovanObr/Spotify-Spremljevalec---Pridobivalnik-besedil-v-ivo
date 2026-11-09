"""Player state, devices, queue, liked songs and search (phase 4)."""

import unittest
from unittest.mock import MagicMock

from models.track import Playback
from services import library_service, search_service, spotify_service


def item(tid, name="Song", type_="track"):
    return {
        "id": tid, "type": type_, "uri": f"spotify:{type_}:{tid}", "name": name,
        "duration_ms": 1000, "artists": [{"name": "Artist"}],
        "album": {"name": "Album", "images": [{"url": "big"}]},
    }


class TestPlayerState(unittest.TestCase):

    def test_full_player_state_is_parsed(self):
        playback = Playback.from_spotify({
            "is_playing": True, "progress_ms": 5, "item": item("a"),
            "shuffle_state": True, "repeat_state": "track",
            "device": {"id": "d1", "name": "Laptop", "type": "Computer",
                       "is_active": True, "volume_percent": 40, "supports_volume": True},
        })

        data = playback.to_dict()
        self.assertTrue(data["shuffle"])
        self.assertEqual(data["repeat"], "track")
        self.assertEqual(data["device"]["volume_percent"], 40)

    def test_currently_playing_response_still_works(self):
        playback = Playback.from_spotify({"is_playing": False, "progress_ms": 0, "item": item("a")})

        self.assertFalse(playback.shuffle)
        self.assertEqual(playback.repeat, "off")
        self.assertIsNone(playback.device)

    def test_unknown_repeat_mode_becomes_off(self):
        playback = Playback.from_spotify({"item": item("a"), "repeat_state": "weird"})
        self.assertEqual(playback.repeat, "off")

    def test_get_current_playback_uses_full_state(self):
        spotify = MagicMock()
        spotify.current_playback.return_value = None

        self.assertIsNone(spotify_service.get_current_playback(spotify))
        spotify.current_playback.assert_called_once()


class TestPlayerCommands(unittest.TestCase):

    def setUp(self):
        self.spotify = MagicMock()

    def test_play_tracks_from_offset(self):
        uris = [f"spotify:track:{i}" for i in range(150)]

        spotify_service.play_tracks(self.spotify, uris, "spotify:track:3")

        kwargs = self.spotify.start_playback.call_args.kwargs
        self.assertEqual(len(kwargs["uris"]), 100)
        self.assertEqual(kwargs["offset"], {"uri": "spotify:track:3"})

    def test_devices(self):
        self.spotify.devices.return_value = {"devices": [
            {"id": "d1", "name": "Phone", "type": "Smartphone", "is_active": False,
             "volume_percent": None, "supports_volume": False},
        ]}

        devices = spotify_service.get_devices(self.spotify)

        self.assertEqual(devices[0].name, "Phone")
        self.assertFalse(devices[0].supports_volume)

    def test_transfer_shuffle_repeat_volume(self):
        spotify_service.transfer_playback(self.spotify, "d1")
        spotify_service.set_shuffle(self.spotify, True)
        spotify_service.set_repeat(self.spotify, "context")
        spotify_service.set_volume(self.spotify, 55)

        self.spotify.transfer_playback.assert_called_once_with("d1", force_play=True)
        self.spotify.shuffle.assert_called_once_with(True, device_id=None)
        self.spotify.repeat.assert_called_once_with("context", device_id=None)
        self.spotify.volume.assert_called_once_with(55, device_id=None)

    def test_settings_target_a_device(self):
        spotify_service.set_shuffle(self.spotify, False, "d9")
        self.spotify.shuffle.assert_called_once_with(False, device_id="d9")

    def test_invalid_repeat_and_volume(self):
        with self.assertRaises(ValueError):
            spotify_service.set_repeat(self.spotify, "forever")
        with self.assertRaises(ValueError):
            spotify_service.set_volume(self.spotify, 101)

    def test_queue_drops_repeats_of_the_current_song(self):
        # What Spotify returns for a single song played without a context
        self.spotify.queue.return_value = {
            "currently_playing": item("one"),
            "queue": [item("one")] * 10,
        }

        self.assertEqual(spotify_service.get_queue(self.spotify)["next"], [])

    def test_queue_lists_each_song_once(self):
        self.spotify.queue.return_value = {
            "currently_playing": item("a"),
            "queue": [item("b"), item("c"), item("a"), item("b"), item("d")],
        }

        ids = [t.id for t in spotify_service.get_queue(self.spotify)["next"]]
        self.assertEqual(ids, ["b", "c", "d"])

    def test_track_knows_its_album(self):
        track = Playback.from_spotify({"item": {**item("a"), "album": {"name": "LP", "uri": "spotify:album:x"}}}).track
        self.assertEqual(track.album_uri, "spotify:album:x")

    def test_queue_skips_episodes_and_limits(self):
        self.spotify.queue.return_value = {
            "currently_playing": item("now"),
            "queue": [item("e", type_="episode")] + [item(str(i)) for i in range(30)],
        }

        data = spotify_service.get_queue(self.spotify)

        self.assertEqual(data["current"].id, "now")
        self.assertEqual(len(data["next"]), spotify_service.QUEUE_LIMIT)
        self.assertEqual(data["next"][0].id, "0")


class TestLikedSongs(unittest.TestCase):

    def setUp(self):
        library_service.clear_cache()
        self.spotify = MagicMock()

    def test_liked_page(self):
        self.spotify.current_user_saved_tracks.return_value = {
            "items": [{"added_at": "2026", "track": item("a")}, {"track": None}],
            "total": 3,
        }

        page = library_service.get_liked_tracks(self.spotify, 0)

        self.assertEqual([i.track.id for i in page["items"]], ["a"])
        self.assertEqual(page["next_offset"], 2)

    def test_are_liked_in_chunks(self):
        uris = [f"spotify:track:{i}" for i in range(45)]
        self.spotify.current_user_saved_tracks_contains.side_effect = (
            lambda chunk: [True] * len(chunk)
        )

        result = library_service.are_liked(self.spotify, uris)

        self.assertEqual(len(result), 45)
        self.assertEqual(self.spotify.current_user_saved_tracks_contains.call_count, 2)

    def test_like_and_unlike_clear_cached_list(self):
        self.spotify.current_user_saved_tracks.return_value = {"items": [], "total": 0}
        library_service.get_liked_tracks(self.spotify, 0)

        library_service.set_liked(self.spotify, ["spotify:track:a"], True)
        library_service.get_liked_tracks(self.spotify, 0)
        library_service.set_liked(self.spotify, ["spotify:track:a"], False)

        self.spotify.current_user_saved_tracks_add.assert_called_once_with(["spotify:track:a"])
        self.spotify.current_user_saved_tracks_delete.assert_called_once_with(["spotify:track:a"])
        self.assertEqual(self.spotify.current_user_saved_tracks.call_count, 2)


class TestSearch(unittest.TestCase):

    def setUp(self):
        search_service.clear_cache()
        library_service.clear_cache()
        self.spotify = MagicMock()
        self.spotify.me.return_value = {"id": "me"}
        self.spotify.search.return_value = {
            "tracks": {"items": [item("t1"), None]},
            "artists": {"items": [{"id": "ar", "uri": "spotify:artist:ar", "name": "Band",
                                   "images": [{"url": "img"}]}]},
            "albums": {"items": [{"id": "al", "uri": "spotify:album:al", "name": "LP",
                                  "artists": [{"name": "Band"}], "release_date": "1999-05-01",
                                  "images": []}]},
            "playlists": {"items": [None, {"id": "p", "uri": "spotify:playlist:p", "name": "Mix",
                                           "owner": {"id": "me"}, "items": {"total": 4}}]},
        }

    def test_results_are_normalized(self):
        data = search_service.search(self.spotify, "  band   lp ")

        self.assertEqual(len(data["tracks"]), 1)
        self.assertEqual(data["artists"][0]["image_url"], "img")
        self.assertEqual(data["albums"][0]["year"], "1999")
        self.assertTrue(data["playlists"][0]["is_owned"])
        kwargs = self.spotify.search.call_args.kwargs
        self.assertEqual(kwargs["q"], "band lp")
        self.assertEqual(kwargs["limit"], 10)

    def test_cached_and_empty_query(self):
        search_service.search(self.spotify, "band")
        search_service.search(self.spotify, "BAND")
        self.assertEqual(self.spotify.search.call_count, 1)

        self.assertEqual(search_service.search(self.spotify, "  ")["tracks"], [])


if __name__ == "__main__":
    unittest.main()
