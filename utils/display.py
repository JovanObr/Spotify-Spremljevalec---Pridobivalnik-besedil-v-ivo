from services.lyrics_service import get_lyrics_search_url


def format_duration(milliseconds: int | None) -> str:
    """Convert milliseconds into a readable time format."""

    if milliseconds is None:
        return "--:--"

    total_seconds = max(0, milliseconds // 1000)

    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def display_track(track: dict, playback: dict) -> None:
    """Display information about the currently playing track."""

    artists = ", ".join(
        artist["name"] for artist in track.get("artists", [])
    )

    title = track.get("name", "Unknown")
    album_data = track.get("album", {})
    album = album_data.get("name", "Unknown")

    progress = format_duration(playback.get("progress_ms"))
    duration = format_duration(track.get("duration_ms"))

    images = album_data.get("images", [])
    artwork_url = images[0].get("url") if images else None

    print("\n" + "=" * 55)
    print("                 CURRENTLY PLAYING")
    print("=" * 55)

    print(f"Title:    {title}")
    print(f"Artist:   {artists}")
    print(f"Album:    {album}")
    print(f"Progress: {progress} / {duration}")

    print("\nAlbum Artwork")
    print("-" * 55)

    if artwork_url:
        print(artwork_url)
    else:
        print("No album artwork available.")

    print("\nLyrics")
    print("-" * 55)

    try:
        lyrics_url = get_lyrics_search_url(artists, title)
        print(lyrics_url)
    except ValueError as error:
        print(f"Could not generate lyrics link: {error}")

    print("=" * 55)