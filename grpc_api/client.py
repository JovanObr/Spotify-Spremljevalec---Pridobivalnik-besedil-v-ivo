"""A small wrapper around the generated stub, used by the terminal app."""

import grpc

from grpc_api import companion_pb2 as pb
from grpc_api import companion_pb2_grpc as pb_grpc


DEFAULT_ADDRESS = "127.0.0.1:50051"
# Unary calls that take longer than this give up (AI facts can take a while)
TIMEOUT_SECONDS = 30


class CompanionClient:
    def __init__(self, address: str = DEFAULT_ADDRESS):
        self.address = address
        self._channel = grpc.insecure_channel(address)
        self._stub = pb_grpc.SoundCompanionStub(self._channel)

    def wait_until_ready(self, timeout: float = 3.0) -> bool:
        """True when the server answers; False if it isn't running."""
        try:
            grpc.channel_ready_future(self._channel).result(timeout=timeout)
            return True
        except grpc.FutureTimeoutError:
            return False

    def close(self) -> None:
        self._channel.close()

    # -- Unary calls ----------------------------------------------------------

    def now_playing(self) -> pb.Playback | None:
        response = self._stub.GetNowPlaying(pb.NowPlayingRequest(), timeout=TIMEOUT_SECONDS)
        return response.playback if response.HasField("playback") else None

    def search(self, query: str, limit: int = 10) -> list[pb.Track]:
        response = self._stub.SearchTracks(pb.SearchRequest(query=query, limit=limit), timeout=TIMEOUT_SECONDS)
        return list(response.tracks)

    def lyrics(self, track: pb.Track) -> pb.LyricsResponse:
        return self._stub.GetLyrics(
            pb.LyricsRequest(
                artist=track.artists[0] if track.artists else "",
                title=track.title,
                album=track.album,
                duration_ms=track.duration_ms,
            ),
            timeout=TIMEOUT_SECONDS,
        )

    def facts(self, track: pb.Track, language: str = "English") -> list[str]:
        response = self._stub.GetSongFacts(
            pb.FactsRequest(
                artist=track.artists[0] if track.artists else "",
                title=track.title,
                album=track.album,
                language=language,
            ),
            timeout=TIMEOUT_SECONDS,
        )
        return list(response.facts)

    def control(self, action: int, track: pb.Track | None = None) -> str:
        request = pb.ControlRequest(action=action)
        if track is not None:
            request.track_uri = track.uri
            request.album_uri = track.album_uri
        return self._stub.ControlPlayback(request, timeout=TIMEOUT_SECONDS).message

    # -- Streaming ------------------------------------------------------------

    def watch(self, include_lyrics: bool = True, poll_interval_ms: int = 0):
        """
        The live event stream. Iterate it to receive events as they happen;
        call .cancel() on it to stop.
        """
        return self._stub.WatchPlayback(
            pb.WatchRequest(include_lyrics=include_lyrics, poll_interval_ms=poll_interval_ms)
        )
