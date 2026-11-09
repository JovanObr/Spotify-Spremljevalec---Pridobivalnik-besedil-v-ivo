"""Lyrics from LRCLIB."""

from fastapi import APIRouter, HTTPException, Query

from services import lyrics_service


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
