"""Healthcheck-routes voor de API."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.core.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Antwoordmodel voor de healthcheck."""

    status: Literal["ok"]
    application: str
    version: str
    environment: str
    timestamp: datetime


@router.get(
    "",
    response_model=HealthResponse,
    summary="Controleer de API-status",
)
async def health_check() -> HealthResponse:
    """Controleer of de backend bereikbaar is."""

    settings = get_settings()

    return HealthResponse(
        status="ok",
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
    )