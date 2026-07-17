"""Centrale router voor alle API-routes."""

from fastapi import APIRouter

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.sources import router as sources_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

api_router.include_router(
    sources_router,
    prefix="/sources",
    tags=["Sources"],
)