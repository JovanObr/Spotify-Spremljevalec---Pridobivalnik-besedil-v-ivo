import time
import requests

from utils.spotify_errors import get_retry_delay

from spotipy.exceptions import SpotifyException

from services.spotify_service import create_spotify_client
from utils.display import display_track

ERROR_RETRY_INTERVAL = 15
POLL_INTERVAL = 5

def process_playback(
    playback: dict | None,
    last_track_id: str | None,
    last_playing_state: bool | None,
    last_was_empty: bool,
):
    """Process one Spotify playback response."""

    if not playback or not playback.get("item"):
        if not last_was_empty:
            print("\nNo track is currently playing.")

        return None, None, True

    track = playback["item"]

    if track.get("type") != "track":
        if not last_was_empty:
            print("\nCurrently playing content is not a music track.")

        return None, None, True

    track_id = track.get("id")
    is_playing = playback.get("is_playing", False)

    if track_id != last_track_id:
        display_track(track, playback)

    if is_playing != last_playing_state:
        status = "Playing" if is_playing else "Paused"
        print(f"\nPlayback status: {status}")

    return track_id, is_playing, False

def main():
    print("=" * 50)
    print("          SPOTIFY SOUND COMPANION")
    print("=" * 50)

    print("\nConnecting to Spotify...")

    try:
        spotify = create_spotify_client()
        print("Successfully connected to Spotify!")

    except SpotifyException as error:
        print(f"Could not connect to Spotify: {error}")
        return

    print(f"\nMonitoring playback every {POLL_INTERVAL} seconds.")
    print("Press Ctrl+C to stop.\n")

    last_track_id = None
    last_playing_state = None
    last_was_empty = False

    try:
        while True:
            try:
                playback = spotify.current_user_playing_track()

                last_track_id, last_playing_state, last_was_empty = (
                    process_playback(
                        playback,
                        last_track_id,
                        last_playing_state,
                        last_was_empty,
                    )
                )

                if not playback or not playback.get("item"):
                    if not last_was_empty:
                        print("\nNo track is currently playing.")

                    last_track_id = None
                    last_playing_state = None
                    last_was_empty = True

                else:
                    track = playback["item"]

                    if track.get("type") != "track":
                        if not last_was_empty:
                            print("\nCurrently playing content is not a music track.")

                        last_track_id = None
                        last_playing_state = None
                        last_was_empty = True

                    else:
                        track_id = track.get("id")
                        is_playing = playback.get("is_playing", False)

                        is_new_track = track_id != last_track_id
                        playback_state_changed = (
                            is_playing != last_playing_state
                        )

                        if is_new_track:
                            display_track(track, playback)

                        if playback_state_changed:
                            status = "Playing" if is_playing else "Paused"
                            print(f"\nPlayback status: {status}")

                        last_track_id = track_id
                        last_playing_state = is_playing
                        last_was_empty = False

            except SpotifyException as error:
                retry_delay = get_retry_delay(error)

                if retry_delay is None:
                    return

                time.sleep(retry_delay)
                continue

            except requests.exceptions.RequestException as error:
                print(f"\nNetwork error: {error}")
                print("Retrying in 15 seconds.")
                time.sleep(15)
                continue

            except Exception as error:
                print(f"\nUnexpected application error: {error}")
                print("Retrying in 15 seconds.")
                time.sleep(15)
                continue

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nStopping Spotify Sound Companion...")

    finally:
        print("Application stopped.")


if __name__ == "__main__":
    main()