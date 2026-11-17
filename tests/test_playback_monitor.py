"""What the terminal client (main.py) prints for data it gets over gRPC."""

import unittest

from grpc_api import companion_pb2 as pb
from main import format_event, format_lyrics, format_playback, format_track_line


def playback(is_playing=True):
    return pb.Playback(
        track=pb.Track(title="Song A", artists=["Artist A", "B"], album="Album A", duration_ms=200_000),
        is_playing=is_playing,
        progress_ms=30_000,
        device_name="Laptop",
    )


class TestTerminalFormatting(unittest.TestCase):

    def test_playback_box(self):
        text = "\n".join(format_playback(playback()))

        self.assertIn("Song A", text)
        self.assertIn("Artist A, B  |  Album A", text)
        self.assertIn("Playing on Laptop  00:30 / 03:20", text)

    def test_track_changed_without_lyrics(self):
        event = pb.PlaybackEvent(track_changed=pb.TrackChanged(
            playback=playback(), lyrics=pb.LyricsResponse(found=False)
        ))

        text = "\n".join(format_event(event))

        self.assertIn("Song A", text)
        self.assertIn("No lyrics found", text)

    def test_lyric_line_with_delay(self):
        event = pb.PlaybackEvent(sent_at_ms=1000, lyric_line=pb.LyricLine(time_ms=65_000, text="Hello"))

        self.assertEqual(format_event(event), ["  [01:05] Hello"])
        self.assertEqual(format_event(event, received_at_ms=1004), ["  [01:05] Hello   (4 ms)"])

    def test_pause_event(self):
        event = pb.PlaybackEvent(play_state=pb.PlayStateChanged(is_playing=False, progress_ms=90_000))

        self.assertEqual(format_event(event), ["  -- Paused at 01:30 --"])

    def test_idle_event(self):
        event = pb.PlaybackEvent(idle=pb.Idle(reason="Nothing is playing on Spotify."))

        self.assertIn("Nothing is playing on Spotify. Waiting...", format_event(event)[1])

    def test_synced_and_plain_lyrics(self):
        synced = pb.LyricsResponse(found=True, synced=True, source="LRCLIB",
                                   lines=[pb.LyricLine(time_ms=1000, text="Hi"), pb.LyricLine(time_ms=2000)])
        plain = pb.LyricsResponse(found=True, plain_lyrics="One\nTwo", source="lyrics.ovh")

        self.assertEqual(format_lyrics(synced), ["[00:01] Hi", "[00:02] ♪", "(Lyrics from LRCLIB)"])
        self.assertEqual(format_lyrics(plain), ["One", "Two", "(Lyrics from lyrics.ovh)"])

    def test_search_result_line(self):
        line = format_track_line(3, pb.Track(title="Song", artists=["X"], duration_ms=61_000, is_playable=False))

        self.assertEqual(line, "  3. Song - X [01:01]  (not playable)")


if __name__ == "__main__":
    unittest.main()
