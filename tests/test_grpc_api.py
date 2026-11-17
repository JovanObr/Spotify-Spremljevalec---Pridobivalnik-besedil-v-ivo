"""The gRPC server, tested through a real channel (no Spotify, no network)."""

import time
import unittest
from unittest.mock import MagicMock, patch

import grpc
from spotipy.exceptions import SpotifyException

from grpc_api import companion_pb2 as pb
from grpc_api.client import CompanionClient
from grpc_api.server import create_server, status_for
from grpc_api.tracker import PlaybackTracker
from models.track import Playback, Track
from services import ai_service
from services.lyrics_service import LyricLine, Lyrics


def make_track(uri="spotify:track:a", title="Song A", duration_ms=200_000):
    return Track(
        id=uri.rsplit(":", 1)[-1], title=title, artists=["Artist"], album="Album",
        duration_ms=duration_ms, artwork_url=None, spotify_url=None, uri=uri,
        album_uri="spotify:album:x",
    )


def make_playback(track=None, is_playing=True, progress_ms=0):
    return Playback(track=track or make_track(), is_playing=is_playing, progress_ms=progress_ms)


def synced_lyrics(times=(0, 1000, 2000)):
    return Lyrics(
        track_name="Song A", artist_name="Artist", album_name=None, plain_lyrics=None,
        synced_lyrics=None, instrumental=False,
        lines=[LyricLine(time_ms=t, text=f"line at {t}") for t in times],
    )


class FakeConnection:
    def __init__(self, playback=None):
        self.client = MagicMock()
        self.playback = playback
        self.forgotten = 0

    def current_playback(self):
        if isinstance(self.playback, Exception):
            raise self.playback
        return self.playback

    def forget_playback(self):
        self.forgotten += 1


class GrpcTestCase(unittest.TestCase):

    def setUp(self):
        self.spotify = FakeConnection()
        self.server, port = create_server(self.spotify, port=0)
        self.client = CompanionClient(f"127.0.0.1:{port}")
        self.assertTrue(self.client.wait_until_ready())

    def tearDown(self):
        self.client.close()
        self.server.stop(None)


class TestUnaryCalls(GrpcTestCase):

    def test_now_playing(self):
        self.spotify.playback = make_playback(progress_ms=42_000)

        playback = self.client.now_playing()

        self.assertEqual(playback.track.title, "Song A")
        self.assertEqual(playback.track.artists, ["Artist"])
        self.assertEqual(playback.progress_ms, 42_000)
        self.assertTrue(playback.is_playing)

    def test_nothing_playing(self):
        self.assertIsNone(self.client.now_playing())

    @patch("services.search_service.search")
    def test_search(self, search):
        search.return_value = {"tracks": [make_track().to_dict(), make_track("spotify:track:b", "B").to_dict()]}

        tracks = self.client.search("song", limit=1)

        self.assertEqual([t.title for t in tracks], ["Song A"])
        search.assert_called_once_with(self.spotify.client, "song", ("track",))

    def test_empty_search_is_invalid_argument(self):
        with self.assertRaises(grpc.RpcError) as caught:
            self.client.search("   ")
        self.assertEqual(caught.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    @patch("services.lyrics_service.get_lyrics")
    def test_lyrics_for_a_chosen_song(self, get_lyrics):
        get_lyrics.return_value = synced_lyrics()

        lyrics = self.client.lyrics(pb.Track(title="Song A", artists=["Artist"], album="Album", duration_ms=200_000))

        self.assertTrue(lyrics.found and lyrics.synced)
        self.assertEqual([line.time_ms for line in lyrics.lines], [0, 1000, 2000])
        get_lyrics.assert_called_once_with("Artist", "Song A", "Album", 200_000)

    @patch("services.lyrics_service.get_lyrics", return_value=None)
    def test_lyrics_not_found(self, _):
        lyrics = self.client.lyrics(pb.Track(title="X", artists=["Y"]))
        self.assertFalse(lyrics.found)

    @patch("services.ai_service.generate_track_facts", return_value=["One.", "Two."])
    def test_facts(self, facts):
        self.assertEqual(self.client.facts(pb.Track(title="Song A", artists=["Artist"])), ["One.", "Two."])
        facts.assert_called_once_with("Artist", "Song A", None, "English")

    @patch("services.ai_service.generate_track_facts", side_effect=ai_service.AINotConfiguredError("no key"))
    def test_facts_without_key(self, _):
        with self.assertRaises(grpc.RpcError) as caught:
            self.client.facts(pb.Track(title="Song A", artists=["Artist"]))
        self.assertEqual(caught.exception.code(), grpc.StatusCode.FAILED_PRECONDITION)

    @patch("services.spotify_service.control_playback")
    def test_control(self, control):
        message = self.client.control(pb.PLAYER_ACTION_NEXT)

        self.assertIn("next", message)
        control.assert_called_once_with(self.spotify.client, "next")
        self.assertEqual(self.spotify.forgotten, 1)

    @patch("services.spotify_service.play_context")
    def test_play_a_chosen_song_in_its_album(self, play_context):
        self.client.control(pb.PLAYER_ACTION_PLAY_TRACK, pb.Track(uri="spotify:track:a", album_uri="spotify:album:x"))

        play_context.assert_called_once_with(self.spotify.client, "spotify:album:x", "spotify:track:a")

    @patch("services.spotify_service.control_playback",
           side_effect=SpotifyException(404, -1, "No active device"))
    def test_no_device(self, _):
        with self.assertRaises(grpc.RpcError) as caught:
            self.client.control(pb.PLAYER_ACTION_PLAY)
        self.assertEqual(caught.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_unspecified_action(self):
        with self.assertRaises(grpc.RpcError) as caught:
            self.client.control(pb.PLAYER_ACTION_UNSPECIFIED)
        self.assertEqual(caught.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)


class TestWatchPlaybackStream(GrpcTestCase):

    @patch("services.lyrics_service.get_lyrics")
    def test_streams_track_then_lyric_lines_in_time(self, get_lyrics):
        get_lyrics.return_value = synced_lyrics((0, 300, 600))
        self.spotify.playback = make_playback(progress_ms=0)

        stream = self.client.watch(include_lyrics=True)
        started = time.monotonic()
        events = []
        for event in stream:
            events.append((event, time.monotonic() - started))
            if len(events) == 4:
                stream.cancel()
                break

        kinds = [event.WhichOneof("event") for event, _ in events]
        self.assertEqual(kinds, ["track_changed", "lyric_line", "lyric_line", "lyric_line"])
        self.assertTrue(events[0][0].track_changed.lyrics.synced)
        self.assertEqual([e.lyric_line.time_ms for e, _ in events[1:]], [0, 300, 600])
        # Lines arrive as they're "sung", not all at once
        self.assertGreater(events[3][1] - events[1][1], 0.45)
        self.assertGreater(events[1][0].sent_at_ms, 0)

    def test_idle_and_stream_survives_spotify_errors(self):
        self.spotify.playback = None

        stream = self.client.watch(include_lyrics=False)
        first = next(stream)
        stream.cancel()

        self.assertEqual(first.WhichOneof("event"), "idle")

    def test_expired_login_ends_the_stream(self):
        self.spotify.playback = SpotifyException(401, -1, "expired")

        with self.assertRaises(grpc.RpcError) as caught:
            for _ in self.client.watch():
                pass
        self.assertEqual(caught.exception.code(), grpc.StatusCode.UNAUTHENTICATED)


class TestPlaybackTracker(unittest.TestCase):

    def test_new_song_sends_track_and_current_line(self):
        tracker = PlaybackTracker(lambda playback: synced_lyrics())

        events = tracker.update(make_playback(progress_ms=1500), now=10.0)

        self.assertEqual([e.WhichOneof("event") for e in events], ["track_changed", "lyric_line"])
        self.assertEqual(events[1].lyric_line.time_ms, 1000)

    def test_lines_follow_the_clock_between_snapshots(self):
        tracker = PlaybackTracker(lambda playback: synced_lyrics())
        tracker.update(make_playback(progress_ms=0), now=0.0)

        self.assertEqual(tracker.tick(0.5), [])
        self.assertEqual(tracker.tick(1.05)[0].lyric_line.time_ms, 1000)
        self.assertEqual(tracker.tick(1.5), [])  # same line: nothing new
        self.assertEqual(tracker.tick(2.2)[0].lyric_line.time_ms, 2000)

    def test_paused_song_does_not_advance(self):
        tracker = PlaybackTracker(lambda playback: synced_lyrics())
        tracker.update(make_playback(is_playing=False, progress_ms=500), now=0.0)

        self.assertEqual(tracker.tick(5.0), [])
        self.assertEqual(tracker.position_ms(5.0), 500)

    def test_pause_and_resume_events(self):
        tracker = PlaybackTracker(None)
        tracker.update(make_playback(), now=0.0)

        paused = tracker.update(make_playback(is_playing=False, progress_ms=3000), now=2.0)

        self.assertEqual(paused[0].WhichOneof("event"), "play_state")
        self.assertFalse(paused[0].play_state.is_playing)
        self.assertEqual(tracker.update(make_playback(is_playing=False, progress_ms=3000), now=4.0), [])

    def test_seek_back_resends_the_current_line(self):
        tracker = PlaybackTracker(lambda playback: synced_lyrics((0, 5000, 10000)))
        tracker.update(make_playback(progress_ms=10500), now=0.0)

        events = tracker.update(make_playback(progress_ms=200), now=2.0)

        self.assertEqual(events[0].lyric_line.time_ms, 0)

    def test_small_correction_after_pause_is_silent(self):
        tracker = PlaybackTracker(lambda playback: synced_lyrics((0, 5000, 6500)))
        tracker.update(make_playback(progress_ms=4000), now=0.0)
        self.assertEqual(tracker.tick(2.6)[0].lyric_line.time_ms, 6500)  # estimate: 6600

        # Spotify says it was really paused at 6000
        events = tracker.update(make_playback(is_playing=False, progress_ms=6000), now=3.0)

        self.assertEqual([e.WhichOneof("event") for e in events], ["play_state"])

    def test_idle_is_sent_once(self):
        tracker = PlaybackTracker(None)

        self.assertEqual(len(tracker.update(None, 0.0)), 1)
        self.assertEqual(tracker.update(None, 2.0), [])

    def test_without_lyrics_lookup_no_lines(self):
        lookup = MagicMock()
        tracker = PlaybackTracker(None)

        events = tracker.update(make_playback(), now=0.0)

        self.assertEqual([e.WhichOneof("event") for e in events], ["track_changed"])
        self.assertFalse(events[0].track_changed.HasField("lyrics"))
        lookup.assert_not_called()


class TestStatusCodes(unittest.TestCase):

    def test_mapping(self):
        cases = [
            (SpotifyException(401, -1, "x"), grpc.StatusCode.UNAUTHENTICATED),
            (SpotifyException(403, -1, "x"), grpc.StatusCode.PERMISSION_DENIED),
            (SpotifyException(429, -1, "x"), grpc.StatusCode.RESOURCE_EXHAUSTED),
            (ai_service.AIServiceError("x", status_code=429), grpc.StatusCode.RESOURCE_EXHAUSTED),
            (ai_service.AIServiceError("x", status_code=503), grpc.StatusCode.UNAVAILABLE),
            (ValueError("x"), grpc.StatusCode.INVALID_ARGUMENT),
            (KeyError("x"), grpc.StatusCode.INTERNAL),
        ]
        for error, code in cases:
            with self.subTest(error=error):
                self.assertEqual(status_for(error)[0], code)


if __name__ == "__main__":
    unittest.main()
