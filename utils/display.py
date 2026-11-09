from models.track import Playback


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


def display_track(playback: Playback) -> None:
    """Display information about the currently playing track."""

    track = playback.track

    progress = format_duration(playback.progress_ms)
    duration = format_duration(track.duration_ms)

    print("\n" + "=" * 55)
    print("                 CURRENTLY PLAYING")
    print("=" * 55)

    print(f"Title:    {track.title}")
    print(f"Artist:   {track.artist}")
    print(f"Album:    {track.album}")
    print(f"Progress: {progress} / {duration}")

    print("\nAlbum Artwork")
    print("-" * 55)

    print(track.artwork_url or "No album artwork available.")

    print("\nLyrics: open the web interface (python -m api) for live lyrics.")

    print("=" * 55)
