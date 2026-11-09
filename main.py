"""Terminal version of Spotify Sound Companion (see api/ for the web version)."""

import time

import requests

from spotipy.exceptions import SpotifyException

from models.track import Playback
from services.spotify_service import create_spotify_client
from utils.display import display_track
from utils.spotify_errors import get_retry_delay


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

    current = Playback.from_spotify(playback)

    if current is None:
        if not last_was_empty:
            print("\nCurrently playing content is not a music track.")

        return None, None, True

    track_id = current.track.id
    is_playing = current.is_playing

    if track_id != last_track_id:
        display_track(current)

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

    except (SpotifyException, RuntimeError) as error:
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

            except SpotifyException as error:
                retry_delay = get_retry_delay(error)

                if retry_delay is None:
                    return

                time.sleep(retry_delay)
                continue

            except requests.exceptions.RequestException as error:
                print(f"\nNetwork error: {error}")
                print(f"Retrying in {ERROR_RETRY_INTERVAL} seconds.")
                time.sleep(ERROR_RETRY_INTERVAL)
                continue

            except Exception as error:
                print(f"\nUnexpected application error: {error}")
                print(f"Retrying in {ERROR_RETRY_INTERVAL} seconds.")
                time.sleep(ERROR_RETRY_INTERVAL)
                continue

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nStopping Spotify Sound Companion...")

    finally:
        print("Application stopped.")


if __name__ == "__main__":
    main()
