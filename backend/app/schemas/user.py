"""API-schema's voor Civora-gebruikers."""

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


UserRole = Literal[
    "user",
    "admin",
]

Vakgroep = Literal[
    "procesmanagement",
    "data_ai",
    "ict",
    "finance",
]


class AuthenticatedIdentity(BaseModel):
    """Identiteit uit een gevalideerd Supabase-token."""

    id: str
    email: str | None = None


class CurrentUser(BaseModel):
    """Ingelogde Civora-gebruiker inclusief profiel."""

    id: str
    email: str | None = None
    full_name: str
    role: UserRole
    vakgroep: Vakgroep

class ProfileUpdate(BaseModel):
    """Wijzigbare profielgegevens."""

    full_name: str = Field(
        min_length=1,
        max_length=120,
    )

    vakgroep: Vakgroep

    @field_validator(
        "full_name"
    )
    @classmethod
    def normalize_full_name(
        cls,
        value: str,
    ) -> str:
        """Verwijder overbodige spaties."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Naam mag niet leeg zijn."
            )

        return normalized