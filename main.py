"""
Terminal version of Spotify Sound Companion, a gRPC client.

Start the server first (python -m grpc_api), then:  python main.py [--server host:port]

Everything shown here comes from the server over gRPC: the live view uses the
WatchPlayback stream, the menu choices use the single-answer calls.
"""

import argparse
import time

import grpc

from grpc_api import companion_pb2 as pb
from grpc_api.client import DEFAULT_ADDRESS, CompanionClient
from utils.display import format_duration


WIDTH = 60
MENU = """
  1  Live view: song changes and lyrics as they're sung (stream)
  2  What's playing now
  3  Search for a song, then show its lyrics or facts, or play it
  4  Play / pause
  5  Next song
  6  Previous song
  q  Quit
"""


# ---------------------------------------------------------------------------
# Formatting (no I/O, so it's easy to test)
# ---------------------------------------------------------------------------

def artist_names(track: pb.Track) -> str:
    return ", ".join(track.artists) or "Unknown artist"


def format_track_line(index: int, track: pb.Track) -> str:
    duration = format_duration(track.duration_ms or None)
    unplayable = "" if track.is_playable else "  (not playable)"
    return f"{index:>3}. {track.title} - {artist_names(track)} [{duration}]{unplayable}"


def format_playback(playback: pb.Playback) -> list[str]:
    track = playback.track
    state = "Playing" if playback.is_playing else "Paused"
    device = f" on {playback.device_name}" if playback.device_name else ""
    return [
        "=" * WIDTH,
        f"  {track.title}",
        f"  {artist_names(track)}  |  {track.album}",
        f"  {state}{device}  {format_duration(playback.progress_ms)} / {format_duration(track.duration_ms or None)}",
        "=" * WIDTH,
    ]


def format_lyrics(lyrics: pb.LyricsResponse) -> list[str]:
    if not lyrics.found:
        return ["No lyrics found for this song."]
    if lyrics.instrumental:
        return ["This song is instrumental."]
    if lyrics.synced:
        lines = [f"[{format_duration(line.time_ms)}] {line.text or '♪'}" for line in lyrics.lines]
    else:
        lines = lyrics.plain_lyrics.splitlines()
    return lines + [f"(Lyrics from {lyrics.source})"]


def format_event(event: pb.PlaybackEvent, received_at_ms: int | None = None) -> list[str]:
    """What the live view prints for one streamed event."""

    kind = event.WhichOneof("event")

    if kind == "track_changed":
        changed = event.track_changed
        lines = [""] + format_playback(changed.playback)
        if changed.HasField("lyrics"):
            lyrics = changed.lyrics
            if not lyrics.found:
                lines.append("  No lyrics found; song changes will still show up here.")
            elif lyrics.instrumental:
                lines.append("  Instrumental.")
            elif not lyrics.synced:
                lines.append("  Only unsynced lyrics exist for this song (menu 3 shows them).")
        return lines

    if kind == "play_state":
        state = event.play_state
        word = "Resumed" if state.is_playing else "Paused"
        return [f"  -- {word} at {format_duration(state.progress_ms)} --"]

    if kind == "lyric_line":
        line = event.lyric_line
        delay = ""
        if received_at_ms is not None and event.sent_at_ms:
            delay = f"   ({max(0, received_at_ms - event.sent_at_ms)} ms)"
        return [f"  [{format_duration(line.time_ms)}] {line.text or '♪'}{delay}"]

    if kind == "idle":
        return ["", f"  {event.idle.reason} Waiting..."]

    return []


def describe_error(error: grpc.RpcError) -> str:
    code = error.code()
    if code == grpc.StatusCode.UNAVAILABLE and "connect" in (error.details() or "").lower():
        return "The server isn't reachable. Is python -m grpc_api running?"
    if code == grpc.StatusCode.DEADLINE_EXCEEDED:
        return "The server took too long to answer."
    return f"{error.details()} ({code.name})"


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def live_view(client: CompanionClient, show_delay: bool) -> None:
    print("\nLive view. Press Ctrl+C to go back to the menu.")
    stream = client.watch(include_lyrics=True)
    try:
        for event in stream:
            received = int(time.time() * 1000) if show_delay else None
            for line in format_event(event, received):
                print(line, flush=True)
    except KeyboardInterrupt:
        stream.cancel()
        print("\nStopped the live view.")
    except grpc.RpcError as error:
        if error.code() != grpc.StatusCode.CANCELLED:
            print(f"\nThe stream stopped: {describe_error(error)}")


def show_now_playing(client: CompanionClient) -> None:
    playback = client.now_playing()
    if playback is None:
        print("\nNothing is playing on Spotify right now.")
        return
    print()
    print("\n".join(format_playback(playback)))


def search_and_pick(client: CompanionClient) -> None:
    query = input("\nSearch for: ").strip()
    if not query:
        return

    started = time.perf_counter()
    tracks = client.search(query)
    took = (time.perf_counter() - started) * 1000

    if not tracks:
        print("No songs found.")
        return

    print(f"\n{len(tracks)} songs ({took:.0f} ms):")
    for index, track in enumerate(tracks, start=1):
        print(format_track_line(index, track))

    choice = input("\nPick a number (Enter to go back): ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(tracks):
        return
    track = tracks[int(choice) - 1]

    while True:
        action = input(f"\n{track.title}:  [l] lyrics  [f] facts  [p] play  [Enter] back: ").strip().lower()
        if action == "l":
            print()
            print("\n".join(format_lyrics(client.lyrics(track))))
        elif action == "f":
            print("\nAsking the AI...")
            for fact in client.facts(track):
                print(f"  - {fact}")
        elif action == "p":
            print(client.control(pb.PLAYER_ACTION_PLAY_TRACK, track))
        else:
            return


def toggle_play(client: CompanionClient) -> None:
    playback = client.now_playing()
    action = pb.PLAYER_ACTION_PAUSE if playback and playback.is_playing else pb.PLAYER_ACTION_PLAY
    print(client.control(action))


ACTIONS = {
    "1": None,  # live view, handled separately (needs the delay option)
    "2": show_now_playing,
    "3": search_and_pick,
    "4": toggle_play,
    "5": lambda client: print(client.control(pb.PLAYER_ACTION_NEXT)),
    "6": lambda client: print(client.control(pb.PLAYER_ACTION_PREVIOUS)),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Spotify Sound Companion terminal client (gRPC)")
    parser.add_argument("--server", default=DEFAULT_ADDRESS, help=f"server address (default {DEFAULT_ADDRESS})")
    parser.add_argument("--show-delay", action="store_true", help="show how long each lyric line took to arrive")
    args = parser.parse_args()

    print("=" * WIDTH)
    print("SPOTIFY SOUND COMPANION  (terminal, gRPC client)".center(WIDTH))
    print("=" * WIDTH)

    client = CompanionClient(args.server)
    print(f"\nConnecting to the gRPC server at {args.server}...")
    if not client.wait_until_ready():
        print("The server isn't running. Start it first with:  python -m grpc_api")
        return
    print("Connected.")

    try:
        while True:
            print(MENU)
            choice = input("Choose: ").strip().lower()
            if choice in ("q", "quit", "exit"):
                break
            if choice not in ACTIONS:
                continue
            try:
                if choice == "1":
                    live_view(client, args.show_delay)
                else:
                    ACTIONS[choice](client)
            except grpc.RpcError as error:
                print(f"\n{describe_error(error)}")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        client.close()
        print("Bye.")


if __name__ == "__main__":
    main()
