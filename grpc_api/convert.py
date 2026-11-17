"""Turn the app's own models into protobuf messages (and back)."""

from models.track import Playback, Track
from services.lyrics_service import Lyrics

from grpc_api import companion_pb2 as pb


def track_message(track: Track) -> pb.Track:
    return pb.Track(
        id=track.id or "",
        title=track.title,
        artists=track.artists,
        album=track.album or "",
        duration_ms=track.duration_ms or 0,
        uri=track.uri or "",
        album_uri=track.album_uri or "",
        artwork_url=track.artwork_url or "",
        spotify_url=track.spotify_url or "",
        is_playable=track.is_playable,
    )


def track_from_dict(data: dict) -> pb.Track:
    """Search results come as dicts (Track.to_dict())."""
    return pb.Track(
        id=data.get("id") or "",
        title=data.get("title") or "",
        artists=data.get("artists") or [],
        album=data.get("album") or "",
        duration_ms=data.get("duration_ms") or 0,
        uri=data.get("uri") or "",
        album_uri=data.get("album_uri") or "",
        artwork_url=data.get("artwork_url") or "",
        spotify_url=data.get("spotify_url") or "",
        is_playable=data.get("is_playable", True) is not False,
    )


def playback_message(playback: Playback) -> pb.Playback:
    return pb.Playback(
        track=track_message(playback.track),
        is_playing=playback.is_playing,
        progress_ms=playback.progress_ms or 0,
        device_name=playback.device.name if playback.device else "",
        shuffle=playback.shuffle,
        repeat=playback.repeat,
    )


def lyrics_message(lyrics: Lyrics | None) -> pb.LyricsResponse:
    if lyrics is None:
        return pb.LyricsResponse(found=False)

    return pb.LyricsResponse(
        found=True,
        instrumental=lyrics.instrumental,
        synced=bool(lyrics.lines),
        lines=[pb.LyricLine(time_ms=line.time_ms, text=line.text) for line in lyrics.lines],
        plain_lyrics=lyrics.plain_lyrics or "",
        source=lyrics.source or "",
    )
