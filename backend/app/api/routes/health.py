"""Healthcheck-routes voor de API."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Antwoordmodel voor de healthcheck."""

    status: Literal["ok"]
    application: str
    timestamp: datetime


@router.get(
    "",
    response_model=HealthResponse,
    summary="Controleer de API-status",
)
async def health_check() -> HealthResponse:
    """Controleer of de backend bereikbaar is."""

    return HealthResponse(
        status="ok",
        application="Public Inhuur Platform API",
        timestamp=datetime.now(timezone.utc),
    )
