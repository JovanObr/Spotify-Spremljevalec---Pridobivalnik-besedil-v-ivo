"""
Song and artist details: Wikipedia (web scraping) plus the artist's country
from CountryInfoService (SOAP).

Each part can fail on its own (Wikipedia unreachable, the SOAP service
down); the answer then has that part empty and says why in "errors", so the
page shows whatever did work.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from services import country_service, wikipedia_service


router = APIRouter(prefix="/api")
logger = logging.getLogger("uvicorn.error")


@router.get("/details")
def details(
    artist: str = Query(min_length=1, max_length=200),
    title: str = Query(min_length=1, max_length=300),
):
    errors: dict[str, str] = {}

    try:
        found = wikipedia_service.get_details(artist, title)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except wikipedia_service.WikipediaError as error:
        logger.warning("Wikipedia: %s", error)
        raise HTTPException(502, str(error)) from error

    country = None
    origin = found.artist.origin if found.artist else None
    if origin:
        try:
            info = country_service.country_for_origin(origin)
            country = info.to_dict() if info else None
        except country_service.CountryServiceError as error:
            logger.warning("CountryInfoService: %s", error)
            errors["country"] = str(error)

    return {**found.to_dict(), "country": country, "errors": errors}

