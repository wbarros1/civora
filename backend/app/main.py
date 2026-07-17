"""FastAPI-applicatie voor het Public Inhuur Platform."""

from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "API voor het verzamelen, structureren en doorzoekbaar maken "
        "van openbare publieke inhuuropdrachten."
    ),
    version=settings.app_version,
    debug=settings.app_debug,
)

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


@app.get(
    "/",
    tags=["Root"],
    summary="API-startpagina",
)
async def root() -> dict[str, str]:
    """Toon algemene informatie over de API."""

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "documentation": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }