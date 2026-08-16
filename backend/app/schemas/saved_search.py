"""API-schema's voor opgeslagen zoekopdrachten."""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


WorkArrangement = Literal[
    "on_site",
    "hybrid",
    "remote",
    "unknown",
]


EmploymentRelationship = Literal[
    "zzp",
    "secondment",
    "both",
    "unknown",
]


ApplicationStatus = Literal[
    "open",
    "closed",
    "unknown",
]


class SavedSearchFilters(BaseModel):
    """Filters die Civora kan bewaren."""

    search: str | None = None
    client: str | None = None
    province: str | None = None

    work_arrangement: (
        WorkArrangement | None
    ) = None

    employment_relationship: (
        EmploymentRelationship | None
    ) = None

    application_status: (
        ApplicationStatus | None
    ) = None

    @field_validator(
        "search",
        "client",
        "province",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """Normaliseer optionele tekstfilters."""

        if value is None:
            return None

        normalized = value.strip()

        return normalized or None


class SavedSearchCreate(BaseModel):
    """Nieuwe opgeslagen zoekopdracht."""

    name: str = Field(
        min_length=1,
        max_length=120,
    )

    filters: SavedSearchFilters

    @field_validator(
        "name"
    )
    @classmethod
    def normalize_name(
        cls,
        value: str,
    ) -> str:
        """Verwijder witruimte uit de naam."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Naam mag niet leeg zijn."
            )

        return normalized


class SavedSearch(BaseModel):
    """Opgeslagen zoekopdracht."""

    id: str
    user_id: str
    name: str

    filters: SavedSearchFilters

    created_at: datetime
    updated_at: datetime