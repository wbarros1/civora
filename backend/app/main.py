"""FastAPI-applicatie voor het Public Inhuur Platform."""

from fastapi import FastAPI

from backend.app.api.router import api_router

app = FastAPI(
    title="Public Inhuur Platform API",
    description=(
        "API voor het verzamelen, structureren en doorzoekbaar maken "
        "van openbare publieke inhuuropdrachten."
    ),
    version="0.1.0",
)

app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get(
    "/",
    tags=["Root"],
    summary="API-startpagina",
)
async def root() -> dict[str, str]:
    """Toon algemene informatie over de API."""

    return {
        "application": "Public Inhuur Platform API",
        "version": "0.1.0",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }