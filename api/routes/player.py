"""Current playback, playback controls, queue and devices."""

import time

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from api.errors import player_http_error, spotify_http_error
from api.state import SpotifyState, get_spotify_state, require_login
from services import spotify_service


router = APIRouter(prefix="/api")

TRACK_URI = r"^spotify:track:[A-Za-z0-9]+$"


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class SeekRequest(BaseModel):
    position_ms: int = Field(ge=0)


class PlayRequest(BaseModel):
    """
    One of:
    - context_uri: a playlist, album or artist (optionally from offset_uri)
    - track_uri: a single song
    - track_uris: a list of songs, e.g. liked songs (optionally from offset_uri)
    """

    context_uri: str | None = Field(
        default=None, pattern=r"^spotify:(playlist|album|artist):[A-Za-z0-9]+$"
    )
    offset_uri: str | None = Field(default=None, pattern=TRACK_URI)
    track_uri: str | None = Field(default=None, pattern=TRACK_URI)
    track_uris: list[str] | None = Field(
        default=None, min_length=1, max_length=spotify_service.MAX_TRACK_URIS
    )

    @model_validator(mode="after")
    def one_target(self):
        targets = [self.context_uri, self.track_uri, self.track_uris]
        if sum(bool(target) for target in targets) != 1:
            raise ValueError("Give exactly one of context_uri, track_uri or track_uris.")
        for uri in self.track_uris or []:
            if not uri.startswith("spotify:track:"):
                raise ValueError("track_uris may only contain Spotify track URIs.")
        return self


class QueueRequest(BaseModel):
    uri: str = Field(pattern=TRACK_URI)


class TransferRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    play: bool = True


class ShuffleRequest(BaseModel):
    state: bool


class RepeatRequest(BaseModel):
    mode: Literal["off", "context", "track"]


class VolumeRequest(BaseModel):
    percent: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(state: SpotifyState, fetch):
    """Run a read-only Spotify call with the usual error mapping."""
    require_login(state)

    try:
        return fetch()
    except SpotifyException as error:
        raise spotify_http_error(error) from error
    except RequestException as error:
        raise HTTPException(503, f"Network error: {error}") from error


def _run_player_command(state: SpotifyState, command) -> None:
    require_login(state)

    try:
        command()
    except SpotifyException as error:
        raise player_http_error(error) from error
    except RequestException as error:
        raise HTTPException(503, f"Network error: {error}") from error

    # The next /api/now-playing call should ask Spotify again
    state.forget_playback()


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

@router.get("/now-playing")
def now_playing(state: SpotifyState = Depends(get_spotify_state)):
    playback = _read(state, state.current_playback)

    return {
        "playback": playback.to_dict() if playback else None,
        "server_time_ms": int(time.time() * 1000),
    }


@router.get("/queue")
def queue(state: SpotifyState = Depends(get_spotify_state)):
    """What's playing and the next songs in the user's queue."""

    data = _read(state, lambda: spotify_service.get_queue(state.client))

    return {
        "current": data["current"].to_dict() if data["current"] else None,
        "next": [track.to_dict() for track in data["next"]],
    }


@router.get("/devices")
def devices(state: SpotifyState = Depends(get_spotify_state)):
    """Spotify apps and speakers available to play on."""

    items = _read(state, lambda: spotify_service.get_devices(state.client))
    return {"items": [device.to_dict() for device in items]}


# ---------------------------------------------------------------------------
# Commands. Specific paths come before /player/{action}, which matches anything.
# ---------------------------------------------------------------------------

@router.post("/player/seek")
def seek(body: SeekRequest, state: SpotifyState = Depends(get_spotify_state)):
    """Jump to a position in the current track."""

    _run_player_command(state, lambda: spotify_service.seek(state.client, body.position_ms))
    return {"ok": True, "position_ms": body.position_ms}


@router.post("/player/play")
def play(
    body: PlayRequest | None = None,
    state: SpotifyState = Depends(get_spotify_state),
):
    """Resume playback, or start a playlist/album/artist, a song, or a list of songs."""

    if body is None:
        command = lambda: spotify_service.control_playback(state.client, "play")
    elif body.track_uri:
        command = lambda: spotify_service.play_track(state.client, body.track_uri)
    elif body.track_uris:
        command = lambda: spotify_service.play_tracks(
            state.client, body.track_uris, body.offset_uri
        )
    else:
        command = lambda: spotify_service.play_context(
            state.client, body.context_uri, body.offset_uri
        )

    _run_player_command(state, command)
    return {"ok": True, "action": "play"}


@router.post("/player/queue")
def add_to_queue(body: QueueRequest, state: SpotifyState = Depends(get_spotify_state)):
    """Add a song to the end of the user's Spotify queue."""

    _run_player_command(state, lambda: spotify_service.add_to_queue(state.client, body.uri))
    return {"ok": True, "uri": body.uri}


@router.post("/player/transfer")
def transfer(body: TransferRequest, state: SpotifyState = Depends(get_spotify_state)):
    """Move playback to another device."""

    _run_player_command(
        state,
        lambda: spotify_service.transfer_playback(state.client, body.device_id, body.play),
    )
    return {"ok": True, "device_id": body.device_id}


def _active_device_id(state: SpotifyState) -> str | None:
    """
    The device that's playing. Shuffle/repeat/volume are sent to it by ID,
    so Spotify applies them to the device the user sees, not whichever
    device it last considered active.
    """
    try:
        playback = state.current_playback()
    except (SpotifyException, RequestException):
        return None
    device = playback.device if playback else None
    return device.id if device else None


@router.post("/player/shuffle")
def shuffle(body: ShuffleRequest, state: SpotifyState = Depends(get_spotify_state)):
    device_id = _active_device_id(state)
    _run_player_command(
        state, lambda: spotify_service.set_shuffle(state.client, body.state, device_id)
    )
    return {"ok": True, "shuffle": body.state}


@router.post("/player/repeat")
def repeat(body: RepeatRequest, state: SpotifyState = Depends(get_spotify_state)):
    device_id = _active_device_id(state)
    _run_player_command(
        state, lambda: spotify_service.set_repeat(state.client, body.mode, device_id)
    )
    return {"ok": True, "repeat": body.mode}


@router.post("/player/volume")
def volume(body: VolumeRequest, state: SpotifyState = Depends(get_spotify_state)):
    device_id = _active_device_id(state)
    _run_player_command(
        state, lambda: spotify_service.set_volume(state.client, body.percent, device_id)
    )
    return {"ok": True, "percent": body.percent}


@router.post("/player/{action}")
def player(action: str, state: SpotifyState = Depends(get_spotify_state)):
    """Pause or skip on the user's active Spotify device."""

    if action not in spotify_service.PLAYER_ACTIONS:
        raise HTTPException(404, f"Unknown player action: {action}")

    _run_player_command(
        state,
        lambda: spotify_service.control_playback(state.client, action),
    )
    return {"ok": True, "action": action}
