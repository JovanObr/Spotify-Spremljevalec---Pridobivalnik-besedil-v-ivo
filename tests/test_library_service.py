import unittest
from unittest.mock import MagicMock

from models.playlist import PlaylistDetail, PlaylistItem, PlaylistSummary
from services import library_service


def make_playlist(pid="p1", owner="me", total=3, new_names=True, with_items=False,
                  collaborative=False):
    contents = {"total": total, "href": "x"}
    if with_items:
        contents["items"] = []
    key = "items" if new_names else "tracks"
    return {
        "id": pid,
        "uri": f"spotify:playlist:{pid}",
        "name": f"Playlist {pid}",
        "description": "Chill &amp; <a href='x'>calm</a> songs",
        "images": [{"url": "https://img/large"}, {"url": "https://img/small"}],
        "owner": {"id": owner, "display_name": owner.title()},
        "collaborative": collaborative,
        "snapshot_id": "snap1",
        key: contents,
    }


def make_track(tid="t1", **extra):
    return {
        "id": tid,
        "type": "track",
        "uri": f"spotify:track:{tid}",
        "name": f"Song {tid}",
        "duration_ms": 1000,
        "artists": [{"name": "Artist"}],
        "album": {"name": "Album", "images": [{"url": "big"}, {"url": "small"}]},
        **extra,
    }


class TestPlaylistModels(unittest.TestCase):

    def test_summary_with_new_field_names(self):
        summary = PlaylistSummary.from_spotify(make_playlist(), "me")

        self.assertTrue(summary.is_owned)
        self.assertEqual(summary.track_count, 3)
        self.assertEqual(summary.description, "Chill & calm songs")
        self.assertEqual(summary.owner_name, "Me")
        self.assertEqual(summary.image_url, "https://img/large")

    def test_summary_with_old_field_names(self):
        summary = PlaylistSummary.from_spotify(
            make_playlist(new_names=False), "me"
        )

        self.assertEqual(summary.track_count, 3)

    def test_followed_playlist_is_not_owned(self):
        summary = PlaylistSummary.from_spotify(make_playlist(owner="else"), "me")

        self.assertFalse(summary.is_owned)

    def test_collaborative_playlist_counts_as_owned(self):
        summary = PlaylistSummary.from_spotify(
            make_playlist(owner="else", collaborative=True), "me"
        )

        self.assertTrue(summary.is_owned)

    def test_detail_items_unavailable_for_followed_playlist(self):
        detail = PlaylistDetail.from_spotify(make_playlist(owner="else"), "me")

        self.assertFalse(detail.items_available)
        self.assertEqual(detail.snapshot_id, "snap1")

    def test_detail_items_available_when_returned(self):
        detail = PlaylistDetail.from_spotify(
            make_playlist(owner="else", with_items=True), "me"
        )

        self.assertTrue(detail.items_available)

    def test_item_with_new_and_old_names(self):
        new = PlaylistItem.from_spotify({"item": make_track("a")}, 0)
        old = PlaylistItem.from_spotify({"track": make_track("b")}, 1)

        self.assertEqual(new.track.uri, "spotify:track:a")
        self.assertEqual(old.track.id, "b")
        self.assertEqual(new.track.thumbnail_url, "small")

    def test_episodes_and_removed_tracks_are_skipped(self):
        self.assertIsNone(
            PlaylistItem.from_spotify({"item": {"type": "episode"}}, 0)
        )
        self.assertIsNone(PlaylistItem.from_spotify({"item": None}, 0))

    def test_local_files_are_not_playable(self):
        item = PlaylistItem.from_spotify(
            {"is_local": True, "item": make_track("l")}, 0
        )

        self.assertTrue(item.track.is_local)
        self.assertFalse(item.track.is_playable)


class TestLibraryService(unittest.TestCase):

    def setUp(self):
        library_service.clear_cache()
        self.spotify = MagicMock()
        self.spotify.me.return_value = {"id": "me"}

    def test_list_playlists_follows_pages(self):
        self.spotify.current_user_playlists.side_effect = [
            {"items": [make_playlist("a"), make_playlist("b", owner="x")],
             "next": "more"},
            {"items": [make_playlist("c")], "next": None},
        ]

        playlists = library_service.list_playlists(self.spotify)

        self.assertEqual([p.id for p in playlists], ["a", "b", "c"])
        self.assertEqual([p.is_owned for p in playlists], [True, False, True])
        second_call = self.spotify.current_user_playlists.call_args_list[1]
        self.assertEqual(second_call.kwargs["offset"], 2)

    def test_list_playlists_is_cached(self):
        self.spotify.current_user_playlists.return_value = {
            "items": [make_playlist("a")], "next": None
        }

        library_service.list_playlists(self.spotify)
        library_service.list_playlists(self.spotify)

        self.assertEqual(self.spotify.current_user_playlists.call_count, 1)
        self.assertEqual(self.spotify.me.call_count, 1)

    def test_playlist_items_page(self):
        self.spotify.playlist.return_value = make_playlist("a")
        self.spotify.playlist_items.return_value = {
            "items": [
                {"item": make_track("1")},
                {"item": {"type": "episode"}},
                {"item": make_track("3")},
            ],
            "total": 5,
        }

        page = library_service.get_playlist_items(self.spotify, "a", offset=0)

        self.assertEqual([i.track.id for i in page["items"]], ["1", "3"])
        self.assertEqual([i.position for i in page["items"]], [0, 2])
        self.assertEqual(page["next_offset"], 3)

    def test_last_page_has_no_next_offset(self):
        self.spotify.playlist.return_value = make_playlist("a")
        self.spotify.playlist_items.return_value = {
            "items": [{"item": make_track("1")}], "total": 51,
        }

        page = library_service.get_playlist_items(self.spotify, "a", offset=50)

        self.assertIsNone(page["next_offset"])

    def test_items_cache_follows_snapshot(self):
        self.spotify.playlist.return_value = make_playlist("a")
        self.spotify.playlist_items.return_value = {"items": [], "total": 0}

        library_service.get_playlist_items(self.spotify, "a")
        library_service.get_playlist_items(self.spotify, "a")
        self.assertEqual(self.spotify.playlist_items.call_count, 1)

        # The playlist was edited: new snapshot, so items are fetched again
        library_service._detail_cache.clear()
        self.spotify.playlist.return_value = {
            **make_playlist("a"), "snapshot_id": "snap2"
        }
        library_service.get_playlist_items(self.spotify, "a")
        self.assertEqual(self.spotify.playlist_items.call_count, 2)


if __name__ == "__main__":
    unittest.main()
