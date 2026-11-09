"""
AI features powered by Google Gemini (AI Studio):

- facts about the current song (fast model, GEMINI_FACTS_MODEL)
- songs you might like if you like the current one
  (GEMINI_RECOMMENDATIONS_MODEL, Gemma 4 31B by default)

Gemini models are called through the google-genai SDK's Interactions API
with a JSON schema. Gemma models are called through generate_content, the
API Google documents for them; if a Gemma model refuses the JSON schema,
the format is described in the prompt instead and parsed leniently.
"""

from functools import lru_cache

from pydantic import BaseModel, Field, ValidationError

import json
import re

from core.config import (
    get_gemini_config,
    get_gemini_facts_model,
    get_gemini_recommendations_model,
)
from utils.single_flight import SingleFlight


MAX_FACTS = 3
# More candidates than we show: some won't exist on Spotify and get dropped
MAX_SUGGESTIONS = 5
DEFAULT_LANGUAGE = "English"

_in_flight = SingleFlight()

SYSTEM_INSTRUCTION = (
    "You are a knowledgeable, concise music journalist. "
    "You write short, interesting, accurate facts about songs and artists. "
    "Only state things you are confident are true. If you know little about "
    "the specific song, write about the artist or the album instead. "
    "Give fewer facts rather than guessing. Never invent chart positions, "
    "dates, quotes or collaborators."
)


class TrackFacts(BaseModel):
    facts: list[str] = Field(
        min_length=1,
        max_length=MAX_FACTS,
        description=(
            "Interesting facts about the song or its artist. "
            "Each fact is one or two sentences, at most 40 words."
        ),
    )


class SongSuggestion(BaseModel):
    title: str = Field(description="Exact song title as released.")
    artist: str = Field(description="Main artist, exactly as credited.")
    reason: str = Field(
        description=(
            "Why someone who likes the given song would like this one, "
            "in one short sentence (at most 18 words). Refer to sound, mood, "
            "era or scene, not to popularity."
        ),
    )


class SongSuggestions(BaseModel):
    songs: list[SongSuggestion] = Field(min_length=1, max_length=MAX_SUGGESTIONS)


RECOMMENDATION_INSTRUCTION = (
    "You are a music curator with deep knowledge of every genre and era. "
    "You recommend real, released songs that are available on Spotify. "
    "Never invent songs or attribute a song to the wrong artist; if unsure "
    "whether a song exists, pick another. Prefer songs that match the sound "
    "and mood over simply the most famous songs."
)


class AIServiceError(Exception):
    """Raised when the AI service cannot generate a response."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class AINotConfiguredError(AIServiceError):
    """Raised when no Gemini API key has been configured."""


@lru_cache(maxsize=1)
def _get_client():
    """Create the Gemini client once and reuse it."""
    from google import genai

    try:
        api_key, _ = get_gemini_config()
    except RuntimeError as error:
        raise AINotConfiguredError(str(error)) from error

    return genai.Client(api_key=api_key)


def is_configured() -> bool:
    try:
        get_gemini_config()
        return True
    except RuntimeError:
        return False


def _build_prompt(artist: str, title: str, album: str | None, language: str):
    album_line = f'Album: "{album}"\n' if album else ""

    return (
        f"Song: \"{title}\"\n"
        f"Artist: {artist}\n"
        f"{album_line}\n"
        f"Write up to {MAX_FACTS} interesting facts about this song and its "
        f"artist. Write them in {language}."
    )


def thinking_config(model: str) -> dict:
    """
    Fastest thinking setting per model family.

    Flash-Lite models already default to "minimal" (their fastest level and
    one they don't accept as "low"), so nothing is sent. Gemini 3.8 Flash
    no longer supports "minimal"; "low" is its fastest.
    """
    if "flash-lite" in model:
        return {}
    return {"thinking_level": "low"}


def _is_thinking_error(error) -> bool:
    message = str(getattr(error, "message", "") or error).lower()
    return getattr(error, "code", None) == 400 and "thinking" in message


def is_gemma(model: str) -> bool:
    return model.lower().startswith("gemma")


_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_answer(text: str, schema: type[BaseModel]):
    """
    Parse a model's JSON answer. Tolerates code fences and text around the
    JSON object, which models sometimes add when no schema is enforced.
    """
    cleaned = _CODE_FENCE.sub("", text.strip())

    try:
        return schema.model_validate_json(cleaned)
    except ValidationError:
        pass

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return schema.model_validate(json.loads(cleaned[start:end + 1]))
        except (ValueError, ValidationError):
            pass

    raise AIServiceError("The AI returned an answer in an unexpected format.")


def _ask_gemma(model: str, system_instruction: str, prompt: str, schema: type[BaseModel]):
    """Gemma via generate_content, with a fallback for schema-less JSON."""
    from google.genai import errors

    client = _get_client()

    try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "response_json_schema": schema.model_json_schema(),
                },
            )
        except errors.APIError as error:
            if error.code != 400:
                raise
            # The model rejected JSON mode or system instructions:
            # put everything in the prompt and parse the reply leniently
            response = client.models.generate_content(
                model=model,
                contents=(
                    f"{system_instruction}\n\n{prompt}\n\n"
                    "Reply with only a JSON object (no other text) that "
                    "matches this JSON schema:\n"
                    f"{json.dumps(schema.model_json_schema())}"
                ),
            )
    except errors.APIError as error:
        raise AIServiceError(
            f"Gemma request failed ({error.code}): {error.message}",
            status_code=error.code,
        ) from error
    except Exception as error:  # network problems, timeouts ...
        raise AIServiceError(f"Gemma request failed: {error}") from error

    text = getattr(response, "text", None)
    if not text:
        raise AIServiceError("Gemma returned an empty response.")

    return parse_json_answer(text, schema)


def _ask(model: str, system_instruction: str, prompt: str, schema: type[BaseModel]):
    """
    Send one structured request and return the parsed response.

    Raises AIServiceError on API errors, empty or malformed answers.
    """
    if is_gemma(model):
        return _ask_gemma(model, system_instruction, prompt, schema)

    from google.genai import errors

    client = _get_client()

    request = {
        "model": model,
        "system_instruction": system_instruction,
        "input": prompt,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema.model_json_schema(),
        },
    }
    # Gemini 3 models ignore/reject temperature and top_p, so none are sent
    generation_config = thinking_config(model)
    if generation_config:
        request["generation_config"] = generation_config

    try:
        try:
            interaction = client.interactions.create(**request)
        except errors.APIError as error:
            # A model that rejects the thinking setting: retry with its default
            if "generation_config" in request and _is_thinking_error(error):
                request.pop("generation_config")
                interaction = client.interactions.create(**request)
            else:
                raise
    except errors.APIError as error:
        raise AIServiceError(
            f"Gemini request failed ({error.code}): {error.message}",
            status_code=error.code,
        ) from error
    except Exception as error:  # network problems, timeouts ...
        raise AIServiceError(f"Gemini request failed: {error}") from error

    text = getattr(interaction, "output_text", None)

    if not text:
        raise AIServiceError("Gemini returned an empty response.")

    return parse_json_answer(text, schema)


def _require_configured():
    if not is_configured():
        raise AINotConfiguredError(
            "No Gemini API key configured. Set GEMINI_API_KEY in .env."
        )


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------

@lru_cache(maxsize=128)
def _generate(
    artist: str,
    title: str,
    album: str | None,
    language: str,
) -> tuple[str, ...]:
    facts = _ask(
        get_gemini_facts_model(),
        SYSTEM_INSTRUCTION,
        _build_prompt(artist, title, album, language),
        TrackFacts,
    ).facts

    cleaned = tuple(fact.strip() for fact in facts if fact.strip())

    if not cleaned:
        raise AIServiceError("Gemini returned no facts.")

    return cleaned[:MAX_FACTS]


def generate_track_facts(
    artist: str,
    title: str,
    album: str | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> list[str]:
    """
    Generate up to three interesting facts about a song and its artist.

    Results are cached per track, so re-opening the same song does not
    spend another API request.

    Returns:
        A list of one to three facts.

    Raises:
        ValueError: If artist or title is empty.
        AINotConfiguredError: If GEMINI_API_KEY is missing.
        AIServiceError: If fact generation fails.
    """

    artist = artist.strip()
    title = title.strip()
    album = album.strip() if album else None

    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    _require_configured()

    # A request for the same song already running (e.g. prefetching) is
    # waited for; its result then comes from the cache
    with _in_flight.lock((artist, title, album, language)):
        return list(_generate(artist, title, album, language))


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _recommendation_prompt(artist: str, title: str, album: str | None) -> str:
    album_line = f'Album: "{album}"\n' if album else ""

    return (
        f'Song: "{title}"\n'
        f"Artist: {artist}\n"
        f"{album_line}\n"
        f"Recommend {MAX_SUGGESTIONS} songs that someone who loves this song "
        "would enjoy. Rules:\n"
        "- Do not include this song.\n"
        f"- At most one song by {artist}; the rest by other artists.\n"
        "- No two songs by the same artist.\n"
        "- Write the title and artist exactly as they appear on Spotify."
    )


@lru_cache(maxsize=128)
def _suggest(artist: str, title: str, album: str | None) -> tuple[SongSuggestion, ...]:
    model = get_gemini_recommendations_model()

    songs = _ask(
        model,
        RECOMMENDATION_INSTRUCTION,
        _recommendation_prompt(artist, title, album),
        SongSuggestions,
    ).songs

    cleaned = tuple(
        SongSuggestion(
            title=song.title.strip(),
            artist=song.artist.strip(),
            reason=song.reason.strip(),
        )
        for song in songs
        if song.title.strip() and song.artist.strip()
    )

    if not cleaned:
        raise AIServiceError("Gemini returned no recommendations.")

    return cleaned[:MAX_SUGGESTIONS]


def suggest_similar_songs(
    artist: str,
    title: str,
    album: str | None = None,
) -> list[SongSuggestion]:
    """
    Ask Gemini for up to five songs similar to the given one.

    These are only candidates: they still have to be found on Spotify
    (see services/recommendation_service.py). Cached per song.

    Raises:
        ValueError: If artist or title is empty.
        AINotConfiguredError: If GEMINI_API_KEY is missing.
        AIServiceError: If the request fails.
    """
    artist = artist.strip()
    title = title.strip()
    album = album.strip() if album else None

    if not artist or not title:
        raise ValueError("Artist and title must not be empty.")

    _require_configured()

    with _in_flight.lock(("suggest", artist, title, album)):
        return list(_suggest(artist, title, album))


def clear_cache() -> None:
    """Forget cached answers and the client (used by tests)."""
    _generate.cache_clear()
    _suggest.cache_clear()
    _get_client.cache_clear()
