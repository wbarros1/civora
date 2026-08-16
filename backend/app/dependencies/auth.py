"""FastAPI-authenticatie via Supabase Auth."""

import logging
from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from backend.app.database.client import (
    get_supabase_client,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)


logger = logging.getLogger(
    __name__
)


bearer_scheme = HTTPBearer(
    auto_error=False
)


def get_current_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedIdentity:
    """Valideer het Supabase access token."""

    if credentials is None:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Authenticatie vereist."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if (
        credentials.scheme.casefold()
        != "bearer"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Ongeldig authenticatieschema."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    token = (
        credentials.credentials
        .strip()
    )

    if not token:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Access token ontbreekt."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        client = (
            get_supabase_client()
        )

        response = (
            client.auth.get_user(
                token
            )
        )

        user = response.user

    except Exception as exc:
        logger.info(
            "Supabase access token "
            "kon niet worden gevalideerd."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Ongeldige of verlopen sessie."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Gebruiker kon niet "
                "worden gevalideerd."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return AuthenticatedIdentity(
        id=str(
            user.id
        ),
        email=(
            str(user.email)
            if user.email
            else None
        ),
    )