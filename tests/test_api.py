import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from spotipy.exceptions import SpotifyException

from api.app import app
from api.routes.auth import safe_next_url
from api.state import get_spotify_state
from models.track import Playback
from services.ai_service import AINotConfiguredError, AIServiceError
from services.lyrics_service import Lyrics, LyricsRateLimitError


SPOTIFY_RESPONSE = {
    "is_playing": True,
    "progress_ms": 42000,
    "item": {
        "id": "track_a",
        "type": "track",
        "name": "Song A",
        "duration_ms": 200000,
        "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
        "album": {
            "name": "Album A",
            "images": [{"url": "https://img/large"}, {"url": "https://img/s"}],
        },
        "external_urls": {"spotify": "https://open.spotify.com/track/a"},
    },
}


class TestApi(unittest.TestCase):

    def setUp(self):
        self.state = MagicMock()
        self.state.is_authenticated.return_value = True
        self.state.current_playback.return_value = Playback.from_spotify(
            SPOTIFY_RESPONSE
        )

        app.dependency_overrides[get_spotify_state] = lambda: self.state
        self.addCleanup(app.dependency_overrides.clear)

        self.client = TestClient(app)

    # --- status / auth -----------------------------------------------------

    def test_status(self):
        with patch("services.ai_service.is_configured", return_value=False), \
             patch("services.musicatlas_service.is_configured", return_value=True):
            response = self.client.get("/api/status")

        self.assertEqual(response.json(), {
            "authenticated": True, "ai_enabled": False, "recommendations_enabled": True,
        })

    def test_token_for_web_playback(self):
        self.state.auth_manager.validate_token.return_value = {
            "access_token": "abc", "expires_at": 123, "scope": "streaming user-read-email",
        }

        response = self.client.get("/api/token")

        self.assertEqual(response.json(), {"access_token": "abc", "expires_at": 123})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_token_without_streaming_scope(self):
        self.state.auth_manager.validate_token.return_value = {
            "access_token": "abc", "expires_at": 123, "scope": "user-read-email",
        }

        self.assertEqual(self.client.get("/api/token").status_code, 403)

    def test_token_when_logged_out(self):
        self.state.auth_manager.validate_token.return_value = None

        self.assertEqual(self.client.get("/api/token").status_code, 401)

    def test_login_redirects_to_spotify_with_safe_state(self):
        self.state.auth_manager.get_authorize_url.return_value = (
            "https://accounts.spotify.com/authorize?x=1"
        )

        response = self.client.get(
            "/login",
            params={"next": "https://evil.example.com"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 307)
        self.state.auth_manager.get_authorize_url.assert_called_with(state="/")

    def test_callback_exchanges_code_and_returns_to_frontend(self):
        response = self.client.get(
            "/callback",
            params={"code": "abc", "state": "http://127.0.0.1:5173"},
            follow_redirects=False,
        )

        self.state.auth_manager.get_access_token.assert_called_once()
        self.assertEqual(
            response.headers["location"], "http://127.0.0.1:5173"
        )

    def test_callback_with_error_reports_it(self):
        response = self.client.get(
            "/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )

        self.assertEqual(
            response.headers["location"], "/?auth_error=access_denied"
        )

    # --- now playing -------------------------------------------------------

    def test_now_playing_returns_normalized_track(self):
        data = self.client.get("/api/now-playing").json()
        track = data["playback"]["track"]

        self.assertEqual(track["id"], "track_a")
        self.assertEqual(track["artist"], "Artist A, Artist B")
        self.assertEqual(track["artwork_url"], "https://img/large")
        self.assertEqual(data["playback"]["progress_ms"], 42000)
        self.assertIn("server_time_ms", data)

    def test_now_playing_when_nothing_plays(self):
        self.state.current_playback.return_value = None

        data = self.client.get("/api/now-playing").json()

        self.assertIsNone(data["playback"])

    def test_now_playing_requires_login(self):
        self.state.is_authenticated.return_value = False

        self.assertEqual(
            self.client.get("/api/now-playing").status_code, 401
        )

    def test_now_playing_passes_on_rate_limit(self):
        self.state.current_playback.side_effect = SpotifyException(
            429, -1, "rate limited", headers={"Retry-After": "12"}
        )

        response = self.client.get("/api/now-playing")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "12")

    # --- player controls -----------------------------------------------

    @patch("services.spotify_service.control_playback")
    def test_player_action(self, mock_control):
        response = self.client.post("/api/player/next")

        self.assertEqual(response.status_code, 200)
        mock_control.assert_called_once_with(self.state.client, "next")
        self.state.forget_playback.assert_called_once()

    def test_player_unknown_action(self):
        self.assertEqual(
            self.client.post("/api/player/teleport").status_code, 404
        )

    @patch("services.spotify_service.control_playback")
    def test_player_without_active_device(self, mock_control):
        mock_control.side_effect = SpotifyException(
            404, -1, "no device", reason="NO_ACTIVE_DEVICE"
        )

        response = self.client.post("/api/player/play")

        self.assertEqual(response.status_code, 409)
        self.assertIn("No active Spotify device", response.json()["detail"])

    @patch("services.spotify_service.control_playback")
    def test_player_requires_premium(self, mock_control):
        mock_control.side_effect = SpotifyException(
            403, -1, "premium", reason="PREMIUM_REQUIRED"
        )

        response = self.client.post("/api/player/pause")

        self.assertEqual(response.status_code, 403)
        self.assertIn("Premium", response.json()["detail"])

    @patch("services.spotify_service.seek")
    def test_seek(self, mock_seek):
        response = self.client.post(
            "/api/player/seek", json={"position_ms": 61000}
        )

        self.assertEqual(response.status_code, 200)
        mock_seek.assert_called_once_with(self.state.client, 61000)
        self.state.forget_playback.assert_called_once()

    def test_seek_rejects_negative_position(self):
        response = self.client.post(
            "/api/player/seek", json={"position_ms": -5}
        )

        self.assertEqual(response.status_code, 422)

    @patch("services.spotify_service.seek")
    def test_seek_without_active_device(self, mock_seek):
        mock_seek.side_effect = SpotifyException(
            404, -1, "no device", reason="NO_ACTIVE_DEVICE"
        )

        response = self.client.post(
            "/api/player/seek", json={"position_ms": 1000}
        )

        self.assertEqual(response.status_code, 409)

    def test_unknown_api_path_is_404(self):
        self.assertEqual(self.client.get("/api/nope").status_code, 404)

    def test_player_requires_login(self):
        self.state.is_authenticated.return_value = False

        self.assertEqual(
            self.client.post("/api/player/play").status_code, 401
        )

    # --- playlists -------------------------------------------------------

    @patch("services.library_service.list_playlists")
    def test_playlists(self, mock_list):
        from models.playlist import PlaylistSummary
        mock_list.return_value = [
            PlaylistSummary("a", "spotify:playlist:a", "A", None, None,
                            "Me", True, 4),
        ]

        data = self.client.get("/api/playlists").json()

        self.assertEqual(data["items"][0]["name"], "A")
        self.assertTrue(data["items"][0]["is_owned"])

    def _detail(self, available=True):
        from models.playlist import PlaylistDetail
        return PlaylistDetail("a", "spotify:playlist:a", "A", None, None,
                              "Me", available, 4, "snap", available)

    @patch("services.library_service.get_playlist")
    def test_playlist_detail(self, mock_get):
        mock_get.return_value = self._detail()

        data = self.client.get("/api/playlists/a").json()

        self.assertEqual(data["snapshot_id"], "snap")
        self.assertTrue(data["items_available"])

    def test_playlist_id_is_validated(self):
        self.assertEqual(
            self.client.get("/api/playlists/bad%20id").status_code, 422
        )

    @patch("services.library_service.get_playlist_items")
    @patch("services.library_service.get_playlist")
    def test_playlist_items(self, mock_get, mock_items):
        from models.playlist import PlaylistItem
        mock_get.return_value = self._detail()
        mock_items.return_value = {
            "items": [PlaylistItem.from_spotify(
                {"item": {**SPOTIFY_RESPONSE["item"], "uri": "spotify:track:a"}}, 0
            )],
            "total": 1,
            "next_offset": None,
        }

        data = self.client.get("/api/playlists/a/items?offset=0").json()

        self.assertEqual(data["items"][0]["track"]["uri"], "spotify:track:a")
        self.assertIsNone(data["next_offset"])

    @patch("services.library_service.get_playlist")
    def test_playlist_items_not_shared(self, mock_get):
        mock_get.return_value = self._detail(available=False)

        response = self.client.get("/api/playlists/a/items")

        self.assertEqual(response.status_code, 403)
        self.assertIn("own", response.json()["detail"])

    @patch("services.library_service.get_playlist")
    def test_missing_playlist(self, mock_get):
        mock_get.side_effect = SpotifyException(404, -1, "not found")

        self.assertEqual(self.client.get("/api/playlists/zz").status_code, 404)

    @patch("services.spotify_service.play_context")
    def test_play_playlist_from_track(self, mock_play):
        response = self.client.post("/api/player/play", json={
            "context_uri": "spotify:playlist:a",
            "offset_uri": "spotify:track:t1",
        })

        self.assertEqual(response.status_code, 200)
        mock_play.assert_called_once_with(
            self.state.client, "spotify:playlist:a", "spotify:track:t1", None
        )

    @patch("services.spotify_service.control_playback")
    def test_play_without_body_resumes(self, mock_control):
        self.assertEqual(self.client.post("/api/player/play").status_code, 200)
        mock_control.assert_called_once_with(self.state.client, "play")

    def test_play_rejects_bad_uri(self):
        response = self.client.post(
            "/api/player/play", json={"context_uri": "https://evil"}
        )

        self.assertEqual(response.status_code, 422)

    # --- recommendations, queue, single songs -------------------------

    @patch("services.recommendation_service.get_recommendations")
    def test_recommendations(self, mock_recs):
        from models.track import Track
        from services.recommendation_service import Recommendation, RecommendationResult
        track = Track.from_spotify({**SPOTIFY_RESPONSE["item"], "uri": "spotify:track:x"})
        mock_recs.return_value = RecommendationResult(
            [Recommendation(track, "Same mood.")], "musicatlas", ("dreampop",)
        )

        data = self.client.get("/api/recommendations", params={
            "artist": "A", "title": "B", "track_uri": "spotify:track:cur",
        }).json()

        self.assertEqual(data["items"][0]["reason"], "Same mood.")
        self.assertEqual(data["items"][0]["track"]["uri"], "spotify:track:x")
        self.assertEqual(data["source"], "musicatlas")
        self.assertEqual(data["tags"], ["dreampop"])
        mock_recs.assert_called_once_with(
            self.state.client, "A", "B", None, "spotify:track:cur"
        )

    @patch(
        "services.recommendation_service.get_recommendations",
        side_effect=AINotConfiguredError("no key"),
    )
    def test_recommendations_without_ai(self, _):
        response = self.client.get(
            "/api/recommendations", params={"artist": "A", "title": "B"}
        )

        self.assertEqual(response.status_code, 503)

    def test_recommendations_require_login(self):
        self.state.is_authenticated.return_value = False

        response = self.client.get(
            "/api/recommendations", params={"artist": "A", "title": "B"}
        )

        self.assertEqual(response.status_code, 401)

    @patch("services.spotify_service.add_to_queue")
    def test_add_to_queue(self, mock_queue):
        response = self.client.post(
            "/api/player/queue", json={"uri": "spotify:track:x"}
        )

        self.assertEqual(response.status_code, 200)
        mock_queue.assert_called_once_with(self.state.client, "spotify:track:x")

    def test_add_to_queue_rejects_non_tracks(self):
        response = self.client.post(
            "/api/player/queue", json={"uri": "spotify:playlist:x"}
        )

        self.assertEqual(response.status_code, 422)

    @patch("services.spotify_service.play_track")
    def test_play_single_track(self, mock_play):
        response = self.client.post(
            "/api/player/play", json={"track_uri": "spotify:track:x"}
        )

        self.assertEqual(response.status_code, 200)
        mock_play.assert_called_once_with(self.state.client, "spotify:track:x", None)

    @patch("services.spotify_service.play_track")
    def test_play_on_a_chosen_device(self, mock_play):
        response = self.client.post(
            "/api/player/play", json={"track_uri": "spotify:track:x", "device_id": "web1"}
        )

        self.assertEqual(response.status_code, 200)
        mock_play.assert_called_once_with(self.state.client, "spotify:track:x", "web1")

    def test_play_needs_exactly_one_target(self):
        both = self.client.post("/api/player/play", json={
            "track_uri": "spotify:track:x", "context_uri": "spotify:playlist:a",
        })
        neither = self.client.post("/api/player/play", json={})

        self.assertEqual(both.status_code, 422)
        self.assertEqual(neither.status_code, 422)

    # --- phase 4: queue, devices, player settings, liked songs, search ---

    @patch("services.spotify_service.get_queue")
    def test_queue(self, mock_queue):
        from models.track import Track
        track = Track.from_spotify(SPOTIFY_RESPONSE["item"])
        mock_queue.return_value = {"current": track, "next": [track, track]}

        data = self.client.get("/api/queue").json()

        self.assertEqual(data["current"]["title"], "Song A")
        self.assertEqual(len(data["next"]), 2)

    @patch("services.spotify_service.get_devices")
    def test_devices(self, mock_devices):
        from models.track import Device
        mock_devices.return_value = [Device("d1", "Laptop", "Computer", True, 50, True)]

        data = self.client.get("/api/devices").json()

        self.assertEqual(data["items"][0]["name"], "Laptop")

    @patch("services.spotify_service.transfer_playback")
    def test_transfer(self, mock_transfer):
        response = self.client.post("/api/player/transfer", json={"device_id": "d1"})

        self.assertEqual(response.status_code, 200)
        mock_transfer.assert_called_once_with(self.state.client, "d1", True)

    @patch("services.spotify_service.set_shuffle")
    @patch("services.spotify_service.set_repeat")
    @patch("services.spotify_service.set_volume")
    def test_shuffle_repeat_volume(self, mock_volume, mock_repeat, mock_shuffle):
        self.assertEqual(self.client.post("/api/player/shuffle", json={"state": True}).status_code, 200)
        self.assertEqual(self.client.post("/api/player/repeat", json={"mode": "track"}).status_code, 200)
        self.assertEqual(self.client.post("/api/player/volume", json={"percent": 30}).status_code, 200)

        # The playback in setUp has no device, so no device ID is sent
        mock_shuffle.assert_called_once_with(self.state.client, True, None)
        mock_repeat.assert_called_once_with(self.state.client, "track", None)
        mock_volume.assert_called_once_with(self.state.client, 30, None)

    @patch("services.spotify_service.set_shuffle")
    def test_shuffle_targets_the_active_device(self, mock_shuffle):
        self.state.current_playback.return_value = Playback.from_spotify({
            **SPOTIFY_RESPONSE,
            "device": {"id": "phone", "name": "Phone", "type": "Smartphone", "is_active": True},
        })

        self.client.post("/api/player/shuffle", json={"state": False})

        mock_shuffle.assert_called_once_with(self.state.client, False, "phone")

    def test_player_settings_are_validated(self):
        self.assertEqual(self.client.post("/api/player/repeat", json={"mode": "x"}).status_code, 422)
        self.assertEqual(self.client.post("/api/player/volume", json={"percent": 150}).status_code, 422)

    @patch("services.spotify_service.set_volume")
    def test_volume_on_device_without_volume_control(self, mock_volume):
        mock_volume.side_effect = SpotifyException(403, -1, "nope", reason="VOLUME_CONTROL_DISALLOW")

        self.assertEqual(self.client.post("/api/player/volume", json={"percent": 30}).status_code, 409)

    @patch("services.spotify_service.play_tracks")
    def test_play_track_list(self, mock_play):
        response = self.client.post("/api/player/play", json={
            "track_uris": ["spotify:track:a", "spotify:track:b"],
            "offset_uri": "spotify:track:b",
        })

        self.assertEqual(response.status_code, 200)
        mock_play.assert_called_once_with(
            self.state.client, ["spotify:track:a", "spotify:track:b"], "spotify:track:b", None
        )

    def test_play_track_list_rejects_other_uris(self):
        response = self.client.post("/api/player/play", json={"track_uris": ["spotify:album:a"]})
        self.assertEqual(response.status_code, 422)

    @patch("services.spotify_service.play_context")
    def test_play_artist(self, mock_play):
        response = self.client.post("/api/player/play", json={"context_uri": "spotify:artist:a"})
        self.assertEqual(response.status_code, 200)

    @patch("services.library_service.get_liked_tracks")
    def test_liked_tracks(self, mock_liked):
        mock_liked.return_value = {"items": [], "total": 0, "next_offset": None}

        data = self.client.get("/api/library/tracks?offset=50").json()

        self.assertEqual(data["total"], 0)
        mock_liked.assert_called_once_with(self.state.client, 50)

    @patch("services.library_service.are_liked", return_value={"spotify:track:a": True})
    def test_liked_contains(self, _):
        data = self.client.get("/api/library/contains?uris=spotify:track:a").json()
        self.assertEqual(data, {"spotify:track:a": True})

    def test_liked_contains_validates(self):
        response = self.client.get("/api/library/contains?uris=spotify:album:a")
        self.assertEqual(response.status_code, 422)

    @patch("services.library_service.set_liked")
    def test_like_and_unlike(self, mock_set):
        self.client.put("/api/library/tracks", json={"uris": ["spotify:track:a"]})
        self.client.request("DELETE", "/api/library/tracks", json={"uris": ["spotify:track:a"]})

        self.assertEqual(
            [c.args[2] for c in mock_set.call_args_list], [True, False]
        )

    @patch("services.search_service.search")
    def test_search(self, mock_search):
        mock_search.return_value = {"tracks": [], "artists": [], "albums": [], "playlists": []}

        response = self.client.get("/api/search", params={"q": "band", "type": "track,album"})

        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once_with(self.state.client, "band", ("track", "album"))

    def test_search_needs_query(self):
        self.assertEqual(self.client.get("/api/search").status_code, 422)

    # --- lyrics ------------------------------------------------------------

    @patch("services.lyrics_service.get_lyrics")
    def test_lyrics_found(self, mock_get_lyrics):
        mock_get_lyrics.return_value = Lyrics(
            track_name="Song A",
            artist_name="Artist A",
            album_name=None,
            plain_lyrics="Hello",
            synced_lyrics="[00:01.00]Hello",
            instrumental=False,
        )

        data = self.client.get(
            "/api/lyrics",
            params={"artist": "Artist A", "title": "Song A",
                    "duration_ms": 200000},
        ).json()

        self.assertTrue(data["found"])
        self.assertEqual(
            data["lyrics"]["lines"], [{"time_ms": 1000, "text": "Hello"}]
        )
        mock_get_lyrics.assert_called_with(
            "Artist A", "Song A", None, 200000
        )

    @patch("services.lyrics_service.get_lyrics", return_value=None)
    def test_lyrics_not_found(self, _):
        data = self.client.get(
            "/api/lyrics", params={"artist": "A", "title": "B"}
        ).json()

        self.assertEqual(data, {"found": False, "lyrics": None})

    @patch(
        "services.lyrics_service.get_lyrics",
        side_effect=LyricsRateLimitError("20"),
    )
    def test_lyrics_rate_limit(self, _):
        response = self.client.get(
            "/api/lyrics", params={"artist": "A", "title": "B"}
        )

        self.assertEqual(response.status_code, 429)

    def test_lyrics_requires_artist_and_title(self):
        self.assertEqual(
            self.client.get("/api/lyrics", params={"title": "B"}).status_code,
            422,
        )

    # --- facts -------------------------------------------------------------

    @patch(
        "services.ai_service.generate_track_facts",
        return_value=["Fact one."],
    )
    def test_facts(self, mock_generate):
        data = self.client.get(
            "/api/facts", params={"artist": "A", "title": "B"}
        ).json()

        self.assertEqual(data, {"facts": ["Fact one."]})
        mock_generate.assert_called_with("A", "B", None, "English")

    @patch(
        "services.ai_service.generate_track_facts",
        side_effect=AINotConfiguredError("no key"),
    )
    def test_facts_not_configured(self, _):
        response = self.client.get(
            "/api/facts", params={"artist": "A", "title": "B"}
        )

        self.assertEqual(response.status_code, 503)

    @patch(
        "services.ai_service.generate_track_facts",
        side_effect=AIServiceError("quota", status_code=429),
    )
    def test_facts_rate_limited(self, _):
        response = self.client.get(
            "/api/facts", params={"artist": "A", "title": "B"}
        )

        self.assertEqual(response.status_code, 429)


class TestSafeNextUrl(unittest.TestCase):

    def test_allows_local_urls(self):
        for url in ("/", "/x", "http://127.0.0.1:5173", "http://localhost:5173/a"):
            self.assertEqual(safe_next_url(url), url)

    def test_rejects_external_urls(self):
        for url in ("https://evil.com", "//evil.com", "javascript:alert(1)", None):
            self.assertEqual(safe_next_url(url), "/")


if __name__ == "__main__":
    unittest.main()
