class AIServiceError(Exception):
    """Raised when the AI service cannot generate a response."""


def generate_track_facts(artist: str, title: str) -> list[str]:
    """
    Generate three interesting facts about a song and its artist.

    Returns:
        A list containing three facts.

    Raises:
        ValueError: If artist or title is empty.
        AIServiceError: If fact generation fails.
    """

    artist = artist.strip()
    title = title.strip()

    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    raise AIServiceError(
        "No AI provider has been configured."
    )