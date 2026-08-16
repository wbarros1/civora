"""API-routes voor opgeslagen zoekopdrachten."""

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)

from backend.app.dependencies.auth import (
    get_current_identity,
)
from backend.app.repositories.saved_searches import (
    create_saved_search,
    delete_saved_search,
    list_saved_searches,
)
from backend.app.schemas.saved_search import (
    SavedSearch,
    SavedSearchCreate,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()


@router.get(
    "",
    response_model=list[SavedSearch],
    summary="Haal opgeslagen zoekopdrachten op",
)
async def get_saved_searches(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> list[SavedSearch]:
    """Geef alleen zoekopdrachten van de huidige gebruiker."""

    try:
        rows = list_saved_searches(
            identity.id
        )

        return [
            SavedSearch(
                **row
            )
            for row in rows
        ]

    except Exception as exc:
        logger.exception(
            "Opgeslagen zoekopdrachten "
            "konden niet worden opgehaald."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Opgeslagen zoekopdrachten "
                "zijn momenteel niet beschikbaar."
            ),
        ) from exc


@router.post(
    "",
    response_model=SavedSearch,
    status_code=(
        status.HTTP_201_CREATED
    ),
    summary="Bewaar een zoekopdracht",
)
async def save_search(
    payload: SavedSearchCreate,
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> SavedSearch:
    """Bewaar filters voor de huidige gebruiker."""

    try:
        row = create_saved_search(
            user_id=identity.id,
            name=payload.name,
            filters=(
                payload.filters.model_dump(
                    exclude_none=True
                )
            ),
        )

        return SavedSearch(
            **row
        )

    except Exception as exc:
        logger.exception(
            "De zoekopdracht kon "
            "niet worden opgeslagen."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "De zoekopdracht kon "
                "niet worden opgeslagen."
            ),
        ) from exc


@router.delete(
    "/{saved_search_id}",
    status_code=(
        status.HTTP_204_NO_CONTENT
    ),
    summary="Verwijder een zoekopdracht",
)
async def remove_saved_search(
    saved_search_id: str,
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> Response:
    """Verwijder één eigen opgeslagen zoekopdracht."""

    try:
        deleted = delete_saved_search(
            user_id=identity.id,
            saved_search_id=(
                saved_search_id
            ),
        )

    except Exception as exc:
        logger.exception(
            "De opgeslagen zoekopdracht "
            "kon niet worden verwijderd."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "De zoekopdracht kon "
                "niet worden verwijderd."
            ),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Opgeslagen zoekopdracht "
                "niet gevonden."
            ),
        )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )