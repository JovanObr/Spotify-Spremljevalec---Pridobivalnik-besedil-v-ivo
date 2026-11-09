"""Lyrics from LRCLIB."""

from fastapi import APIRouter, HTTPException, Query

from api.errors import ai_http_error
from services import ai_service, lyrics_service


router = APIRouter(prefix="/api")


@router.get("/lyrics")
def lyrics(
    artist: str = Query(min_length=1),
    title: str = Query(min_length=1),
    album: str | None = None,
    duration_ms: int | None = Query(default=None, gt=0),
):
    try:
        result = lyrics_service.get_lyrics(artist, title, album, duration_ms)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except lyrics_service.LyricsRateLimitError as error:
        raise HTTPException(
            429,
            str(error),
            headers={"Retry-After": str(error.retry_after or 30)},
        ) from error
    except lyrics_service.LyricsServiceError as error:
        raise HTTPException(502, str(error)) from error

    return {
        "found": result is not None,
        "lyrics": result.to_dict() if result else None,
    }


def _lyrics_or_error(artist, title, album, duration_ms):
    """The song's lyrics (from cache, usually), mapped to HTTP errors."""
    try:
        return lyrics_service.get_lyrics(artist, title, album, duration_ms)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except lyrics_service.LyricsServiceError as error:
        raise HTTPException(502, str(error)) from error


def lyric_lines(result) -> list[str]:
    """The lines the frontend shows: synced lines, else plain lines."""
    if result.lines:
        return [line.text for line in result.lines]
    return (result.plain_lyrics or "").split("\n")


@router.get("/lyrics/translation")
def translation(
    artist: str = Query(min_length=1),
    title: str = Query(min_length=1),
    language: str = Query(min_length=2, max_length=40),
    album: str | None = None,
    duration_ms: int | None = Query(default=None, gt=0),
):
    """
    The song's lyrics translated line by line. "lines" has one entry per
    displayed lyric line, in the same order as /api/lyrics returns them.
    """
    result = _lyrics_or_error(artist, title, album, duration_ms)
    if result is None or result.instrumental:
        raise HTTPException(404, "This song has no lyrics to translate.")

    lines = lyric_lines(result)

    try:
        translated = ai_service.translate_lyrics(artist, title, lines, language)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except ai_service.AIServiceError as error:
        raise ai_http_error(error) from error

    return {"language": language, "lines": translated}


@router.get("/meaning")
def meaning(
    artist: str = Query(min_length=1),
    title: str = Query(min_length=1),
    album: str | None = None,
    duration_ms: int | None = Query(default=None, gt=0),
    language: str = Query(default=ai_service.DEFAULT_LANGUAGE, max_length=40),
):
    """What the song is about, based on its lyrics when they're available."""

    try:
        result = lyrics_service.get_lyrics(artist, title, album, duration_ms)
    except (ValueError, lyrics_service.LyricsServiceError):
        result = None  # explain without lyrics

    lyrics = None
    if result is not None and not result.instrumental:
        lyrics = "\n".join(line for line in lyric_lines(result) if line.strip()) or None

    try:
        explanation = ai_service.explain_song(artist, title, album, lyrics, language)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except ai_service.AIServiceError as error:
        raise ai_http_error(error) from error

    return {
        "summary": explanation.summary,
        "themes": explanation.themes,
        "based_on_lyrics": lyrics is not None,
    }
