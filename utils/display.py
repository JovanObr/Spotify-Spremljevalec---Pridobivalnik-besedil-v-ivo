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
