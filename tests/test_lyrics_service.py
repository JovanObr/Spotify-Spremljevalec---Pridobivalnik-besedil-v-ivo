from services.lyrics_service import (
    get_lyrics,
    LyricsNotFoundError,
    LyricsServiceError,
)


def main():
    artist = "Coldplay"
    title = "Yellow"

    print(f"Testing lyrics retrieval: {artist} - {title}")

    try:
        lyrics = get_lyrics(artist, title)

        print("\nLyrics retrieved successfully!")
        print(f"Number of characters: {len(lyrics)}")
        print(f"Number of lines: {len(lyrics.splitlines())}")

    except LyricsNotFoundError as error:
        print(f"\nLyrics not found: {error}")

    except LyricsServiceError as error:
        print(f"\nLyrics service error: {error}")


if __name__ == "__main__":
    main()