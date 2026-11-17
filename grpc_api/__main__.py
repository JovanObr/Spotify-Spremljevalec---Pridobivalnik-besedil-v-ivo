"""
Start the gRPC server:  python -m grpc_api  [--port 50051]

Then run the terminal client in another window:  python main.py
"""

import argparse
import logging
import os

from spotipy.exceptions import SpotifyException

from core.config import BASE_DIR
from services.spotify_service import create_auth_manager, create_spotify_client
from utils import persistent_cache

from grpc_api.server import DEFAULT_PORT, SpotifyConnection, create_server


def connect_to_spotify() -> SpotifyConnection:
    """
    Use the saved Spotify login (.cache, shared with the web app). Without
    one, Spotipy opens the browser to log in, like the old terminal app did.
    """
    auth_manager = create_auth_manager(open_browser=True)
    token = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
    if token is None:
        print("Not logged in yet: opening Spotify in your browser...")
        print("(If the web app is running on port 8888, log in there instead and restart this.)")
        auth_manager.get_access_token(as_dict=False)
    return SpotifyConnection(create_spotify_client(auth_manager))


def main() -> None:
    parser = argparse.ArgumentParser(description="Spotify Sound Companion gRPC server")
    parser.add_argument("--port", type=int, default=int(os.getenv("GRPC_PORT", DEFAULT_PORT)))
    args = parser.parse_args()

    # Shares .data/cache.sqlite3 with the web server
    persistent_cache.enable_default(BASE_DIR)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    try:
        spotify = connect_to_spotify()
    except (SpotifyException, RuntimeError) as error:
        raise SystemExit(f"Could not connect to Spotify: {error}")

    server, port = create_server(spotify, args.port)
    print(f"gRPC server listening on 127.0.0.1:{port}. Press Ctrl+C to stop.")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nStopping...")
        server.stop(grace=1).wait()


if __name__ == "__main__":
    main()
