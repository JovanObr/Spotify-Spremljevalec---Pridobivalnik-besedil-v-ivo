"""Music in Slovenia: a SiStat table fetched as a PC-Axis file."""

import logging

from fastapi import APIRouter, HTTPException

from services import stats_service


router = APIRouter(prefix="/api")
logger = logging.getLogger("uvicorn.error")


@router.get("/stats")
def stats():
    """The table: dimensions, cells, title, units and when SiStat last updated it."""
    try:
        return stats_service.get_stats()
    except stats_service.StatsNotConfigured as error:
        raise HTTPException(503, str(error)) from error
    except stats_service.StatsError as error:
        logger.warning("SiStat: %s", error)
        raise HTTPException(502, str(error)) from error
