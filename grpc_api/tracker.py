"""
The logic behind the WatchPlayback stream, kept free of gRPC and clocks so
it can be tested directly.

The server feeds it a fresh Spotify playback snapshot every couple of
seconds (update) and asks it many times per second what changed (tick).
Between snapshots the song position is estimated from the clock, so lyric
lines arrive on time even though Spotify is only asked every 2 seconds.
"""

from bisect import bisect_right
from dataclasses import dataclass
from typing import Callable

from models.track import Playback
from services.lyrics_service import Lyrics

from grpc_api import companion_pb2 as pb
from grpc_api.convert import lyrics_message, playback_message


LyricsLookup = Callable[[Playback], Lyrics | None]

# The estimate runs ahead a little when the song is paused between two
# snapshots. Going back less than this is that correction, not a seek, so the
# previous line isn't printed a second time.
SEEK_BACK_THRESHOLD_MS = 3000


@dataclass
class _Snapshot:
    playback: Playback
    taken_at: float  # seconds, from the same clock as `now`


class PlaybackTracker:
    def __init__(self, lookup_lyrics: LyricsLookup | None):
        # None: the client didn't ask for lyrics
        self._lookup_lyrics = lookup_lyrics
        self._snapshot: _Snapshot | None = None
        self._track_key: str | None = None
        self._is_playing: bool | None = None
        self._idle = False
        self._lines = []
        self._line_times: list[int] = []
        self._line_index = -1

    # -- Snapshots ----------------------------------------------------------

    def update(self, playback: Playback | None, now: float) -> list[pb.PlaybackEvent]:
        """A new answer from Spotify. Returns the events it causes."""

        if playback is None:
            self._snapshot = None
            self._track_key = None
            self._is_playing = None
            self._set_lyrics(None)
            if self._idle:
                return []
            self._idle = True
            return [pb.PlaybackEvent(idle=pb.Idle(reason="Nothing is playing on Spotify."))]

        self._idle = False
        self._snapshot = _Snapshot(playback, now)
        key = playback.track.uri or f"{playback.track.artist}|{playback.track.title}"

        if key != self._track_key:
            self._track_key = key
            self._is_playing = playback.is_playing

            changed = pb.TrackChanged(playback=playback_message(playback))
            if self._lookup_lyrics is not None:
                lyrics = self._lookup_lyrics(playback)
                self._set_lyrics(lyrics)
                changed.lyrics.CopyFrom(lyrics_message(lyrics))
            return [pb.PlaybackEvent(track_changed=changed), *self.tick(now)]

        events = []
        if playback.is_playing != self._is_playing:
            self._is_playing = playback.is_playing
            events.append(pb.PlaybackEvent(play_state=pb.PlayStateChanged(
                is_playing=playback.is_playing,
                progress_ms=playback.progress_ms or 0,
            )))
        return events + self.tick(now)

    # -- Between snapshots --------------------------------------------------

    def position_ms(self, now: float) -> int | None:
        """Where in the song we are now, estimated from the last snapshot."""
        if self._snapshot is None:
            return None
        playback = self._snapshot.playback
        position = playback.progress_ms or 0
        if playback.is_playing:
            position += int((now - self._snapshot.taken_at) * 1000)
        if playback.track.duration_ms:
            position = min(position, playback.track.duration_ms)
        return position

    def tick(self, now: float) -> list[pb.PlaybackEvent]:
        """The lyric line that just started, if any."""
        position = self.position_ms(now)
        if position is None or not self._lines:
            return []

        index = bisect_right(self._line_times, position) - 1
        if (
            0 <= index < self._line_index
            and self._line_times[self._line_index] - position < SEEK_BACK_THRESHOLD_MS
        ):
            return []  # small correction, keep showing the current line
        if index == self._line_index or index < 0:
            self._line_index = index
            return []

        self._line_index = index
        line = self._lines[index]
        return [pb.PlaybackEvent(lyric_line=pb.LyricLine(time_ms=line.time_ms, text=line.text))]

    def _set_lyrics(self, lyrics: Lyrics | None) -> None:
        self._lines = list(lyrics.lines) if lyrics and not lyrics.instrumental else []
        self._line_times = [line.time_ms for line in self._lines]
        self._line_index = -1
