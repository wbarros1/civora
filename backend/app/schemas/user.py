"""API-schema's voor Civora-gebruikers."""

from typing import Literal

from pydantic import BaseModel


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