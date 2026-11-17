from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PlayerAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLAYER_ACTION_UNSPECIFIED: _ClassVar[PlayerAction]
    PLAYER_ACTION_PLAY: _ClassVar[PlayerAction]
    PLAYER_ACTION_PAUSE: _ClassVar[PlayerAction]
    PLAYER_ACTION_NEXT: _ClassVar[PlayerAction]
    PLAYER_ACTION_PREVIOUS: _ClassVar[PlayerAction]
    PLAYER_ACTION_PLAY_TRACK: _ClassVar[PlayerAction]
PLAYER_ACTION_UNSPECIFIED: PlayerAction
PLAYER_ACTION_PLAY: PlayerAction
PLAYER_ACTION_PAUSE: PlayerAction
PLAYER_ACTION_NEXT: PlayerAction
PLAYER_ACTION_PREVIOUS: PlayerAction
PLAYER_ACTION_PLAY_TRACK: PlayerAction

class Track(_message.Message):
    __slots__ = ("id", "title", "artists", "album", "duration_ms", "uri", "album_uri", "artwork_url", "spotify_url", "is_playable")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    ARTISTS_FIELD_NUMBER: _ClassVar[int]
    ALBUM_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    URI_FIELD_NUMBER: _ClassVar[int]
    ALBUM_URI_FIELD_NUMBER: _ClassVar[int]
    ARTWORK_URL_FIELD_NUMBER: _ClassVar[int]
    SPOTIFY_URL_FIELD_NUMBER: _ClassVar[int]
    IS_PLAYABLE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    artists: _containers.RepeatedScalarFieldContainer[str]
    album: str
    duration_ms: int
    uri: str
    album_uri: str
    artwork_url: str
    spotify_url: str
    is_playable: bool
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., artists: _Optional[_Iterable[str]] = ..., album: _Optional[str] = ..., duration_ms: _Optional[int] = ..., uri: _Optional[str] = ..., album_uri: _Optional[str] = ..., artwork_url: _Optional[str] = ..., spotify_url: _Optional[str] = ..., is_playable: _Optional[bool] = ...) -> None: ...

class Playback(_message.Message):
    __slots__ = ("track", "is_playing", "progress_ms", "device_name", "shuffle", "repeat")
    TRACK_FIELD_NUMBER: _ClassVar[int]
    IS_PLAYING_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_MS_FIELD_NUMBER: _ClassVar[int]
    DEVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    SHUFFLE_FIELD_NUMBER: _ClassVar[int]
    REPEAT_FIELD_NUMBER: _ClassVar[int]
    track: Track
    is_playing: bool
    progress_ms: int
    device_name: str
    shuffle: bool
    repeat: str
    def __init__(self, track: _Optional[_Union[Track, _Mapping]] = ..., is_playing: _Optional[bool] = ..., progress_ms: _Optional[int] = ..., device_name: _Optional[str] = ..., shuffle: _Optional[bool] = ..., repeat: _Optional[str] = ...) -> None: ...

class LyricLine(_message.Message):
    __slots__ = ("time_ms", "text")
    TIME_MS_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    time_ms: int
    text: str
    def __init__(self, time_ms: _Optional[int] = ..., text: _Optional[str] = ...) -> None: ...

class NowPlayingRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NowPlayingResponse(_message.Message):
    __slots__ = ("playback",)
    PLAYBACK_FIELD_NUMBER: _ClassVar[int]
    playback: Playback
    def __init__(self, playback: _Optional[_Union[Playback, _Mapping]] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("query", "limit")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    query: str
    limit: int
    def __init__(self, query: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("tracks",)
    TRACKS_FIELD_NUMBER: _ClassVar[int]
    tracks: _containers.RepeatedCompositeFieldContainer[Track]
    def __init__(self, tracks: _Optional[_Iterable[_Union[Track, _Mapping]]] = ...) -> None: ...

class LyricsRequest(_message.Message):
    __slots__ = ("artist", "title", "album", "duration_ms")
    ARTIST_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    ALBUM_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    artist: str
    title: str
    album: str
    duration_ms: int
    def __init__(self, artist: _Optional[str] = ..., title: _Optional[str] = ..., album: _Optional[str] = ..., duration_ms: _Optional[int] = ...) -> None: ...

class LyricsResponse(_message.Message):
    __slots__ = ("found", "instrumental", "synced", "lines", "plain_lyrics", "source")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENTAL_FIELD_NUMBER: _ClassVar[int]
    SYNCED_FIELD_NUMBER: _ClassVar[int]
    LINES_FIELD_NUMBER: _ClassVar[int]
    PLAIN_LYRICS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    found: bool
    instrumental: bool
    synced: bool
    lines: _containers.RepeatedCompositeFieldContainer[LyricLine]
    plain_lyrics: str
    source: str
    def __init__(self, found: _Optional[bool] = ..., instrumental: _Optional[bool] = ..., synced: _Optional[bool] = ..., lines: _Optional[_Iterable[_Union[LyricLine, _Mapping]]] = ..., plain_lyrics: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class FactsRequest(_message.Message):
    __slots__ = ("artist", "title", "album", "language")
    ARTIST_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    ALBUM_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    artist: str
    title: str
    album: str
    language: str
    def __init__(self, artist: _Optional[str] = ..., title: _Optional[str] = ..., album: _Optional[str] = ..., language: _Optional[str] = ...) -> None: ...

class FactsResponse(_message.Message):
    __slots__ = ("facts",)
    FACTS_FIELD_NUMBER: _ClassVar[int]
    facts: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, facts: _Optional[_Iterable[str]] = ...) -> None: ...

class ControlRequest(_message.Message):
    __slots__ = ("action", "track_uri", "album_uri")
    ACTION_FIELD_NUMBER: _ClassVar[int]
    TRACK_URI_FIELD_NUMBER: _ClassVar[int]
    ALBUM_URI_FIELD_NUMBER: _ClassVar[int]
    action: PlayerAction
    track_uri: str
    album_uri: str
    def __init__(self, action: _Optional[_Union[PlayerAction, str]] = ..., track_uri: _Optional[str] = ..., album_uri: _Optional[str] = ...) -> None: ...

class ControlResponse(_message.Message):
    __slots__ = ("ok", "message")
    OK_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    message: str
    def __init__(self, ok: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class WatchRequest(_message.Message):
    __slots__ = ("include_lyrics", "poll_interval_ms")
    INCLUDE_LYRICS_FIELD_NUMBER: _ClassVar[int]
    POLL_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    include_lyrics: bool
    poll_interval_ms: int
    def __init__(self, include_lyrics: _Optional[bool] = ..., poll_interval_ms: _Optional[int] = ...) -> None: ...

class PlaybackEvent(_message.Message):
    __slots__ = ("sent_at_ms", "track_changed", "play_state", "lyric_line", "idle")
    SENT_AT_MS_FIELD_NUMBER: _ClassVar[int]
    TRACK_CHANGED_FIELD_NUMBER: _ClassVar[int]
    PLAY_STATE_FIELD_NUMBER: _ClassVar[int]
    LYRIC_LINE_FIELD_NUMBER: _ClassVar[int]
    IDLE_FIELD_NUMBER: _ClassVar[int]
    sent_at_ms: int
    track_changed: TrackChanged
    play_state: PlayStateChanged
    lyric_line: LyricLine
    idle: Idle
    def __init__(self, sent_at_ms: _Optional[int] = ..., track_changed: _Optional[_Union[TrackChanged, _Mapping]] = ..., play_state: _Optional[_Union[PlayStateChanged, _Mapping]] = ..., lyric_line: _Optional[_Union[LyricLine, _Mapping]] = ..., idle: _Optional[_Union[Idle, _Mapping]] = ...) -> None: ...

class TrackChanged(_message.Message):
    __slots__ = ("playback", "lyrics")
    PLAYBACK_FIELD_NUMBER: _ClassVar[int]
    LYRICS_FIELD_NUMBER: _ClassVar[int]
    playback: Playback
    lyrics: LyricsResponse
    def __init__(self, playback: _Optional[_Union[Playback, _Mapping]] = ..., lyrics: _Optional[_Union[LyricsResponse, _Mapping]] = ...) -> None: ...

class PlayStateChanged(_message.Message):
    __slots__ = ("is_playing", "progress_ms")
    IS_PLAYING_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_MS_FIELD_NUMBER: _ClassVar[int]
    is_playing: bool
    progress_ms: int
    def __init__(self, is_playing: _Optional[bool] = ..., progress_ms: _Optional[int] = ...) -> None: ...

class Idle(_message.Message):
    __slots__ = ("reason",)
    REASON_FIELD_NUMBER: _ClassVar[int]
    reason: str
    def __init__(self, reason: _Optional[str] = ...) -> None: ...
