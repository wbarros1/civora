"""Centrale router voor alle API-routes."""

from fastapi import APIRouter

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.sources import router as sources_router
from backend.app.api.routes.opportunities import (
    router as opportunities_router,
)

from backend.app.api.routes.auth import (
    router as auth_router,
)

from backend.app.api.routes.saved_searches import (
    router as saved_searches_router,
)


api_router = APIRouter()

api_router.include_router(
    saved_searches_router,
    prefix="/saved-searches",
    tags=["Saved searches"],
)

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

api_router.include_router(
    opportunities_router,
    prefix="/opportunities",
    tags=["Opportunities"],
)

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
)