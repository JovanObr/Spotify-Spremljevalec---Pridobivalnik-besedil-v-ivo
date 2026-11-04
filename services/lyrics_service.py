from urllib.parse import quote, quote_plus

import requests


BASE_URL = "https://api.lyrics.ovh/v1"
REQUEST_TIMEOUT = 10


class LyricsNotFoundError(Exception):
    """Raised when lyrics are unavailable for the requested track."""


class LyricsServiceError(Exception):
    """Raised when the lyrics service cannot provide a valid response."""


def get_lyrics_search_url(artist: str, title: str) -> str:
    """Generate a lyrics search URL for a song."""

    artist = artist.strip()
    title = title.strip()

    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    query = quote_plus(f"{artist} {title}")

    return f"https://genius.com/search?q={query}"

def get_lyrics(artist: str, title: str) -> str:
    """
    Retrieve lyrics for a song using its artist and title.

    Raises:
        ValueError: If artist or title is empty.
        LyricsNotFoundError: If no lyrics are found.
        LyricsServiceError: If the API request or response fails.
    """

    artist = artist.strip()
    title = title.strip()

    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    encoded_artist = quote(artist, safe="")
    encoded_title = quote(title, safe="")

    url = f"{BASE_URL}/{encoded_artist}/{encoded_title}"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 404:
            raise LyricsNotFoundError(
                f"No lyrics found for '{title}' by {artist}."
            )

        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        raise LyricsServiceError(
            f"Could not connect to Lyrics.ovh: {error}"
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise LyricsServiceError(
            "Lyrics.ovh returned an invalid JSON response."
        ) from error

    lyrics = data.get("lyrics") if isinstance(data, dict) else None

    if not isinstance(lyrics, str) or not lyrics.strip():
        raise LyricsServiceError(
            "Lyrics.ovh returned an invalid or empty lyrics response."
        )

    return lyrics.strip()