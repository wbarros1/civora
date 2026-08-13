"""FastAPI-applicatie voor het Public Inhuur Platform."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import (
    api_router,
)
from backend.app.core.config import (
    get_settings,
)


settings = get_settings()

FRONTEND_DIRECTORY = (
    Path(__file__).resolve().parent
    / "frontend"
)


app = FastAPI(
    title=settings.app_name,
    description=(
        "API voor het verzamelen, structureren "
        "en doorzoekbaar maken van openbare "
        "publieke inhuuropdrachten."
    ),
    version=settings.app_version,
    debug=settings.app_debug,
)


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


app.mount(
    "/static",
    StaticFiles(
        directory=FRONTEND_DIRECTORY,
    ),
    name="static",
)


@app.get(
    "/",
    include_in_schema=False,
)
async def frontend() -> FileResponse:
    """Toon de Vasco MVP-frontend."""

    return FileResponse(
        FRONTEND_DIRECTORY
        / "index.html"
    )