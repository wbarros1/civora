"""Voorbereiding van structured opportunities voor classificatie."""

import json
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class OpportunityClassificationInput(
    BaseModel
):
    """Inhoud die relevant is voor vakgroepclassificatie."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(
        min_length=1,
        max_length=500,
    )

    client_name: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = Field(
        default=None,
        max_length=1200,
    )

    education_level: str | None = Field(
        default=None,
        max_length=500,
    )

    minimum_years_experience: (
        float | None
    ) = Field(
        default=None,
        ge=0,
        le=80,
    )

    requirements: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    wishes: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    competencies: list[str] = Field(
        default_factory=list,
        max_length=15,
    )

    skills: list[str] = Field(
        default_factory=list,
        max_length=20,
    )


def _optional_text(
    value: Any,
) -> str | None:
    """Normaliseer een optionele tekstwaarde."""

    if not isinstance(
        value,
        str,
    ):
        return None

    normalized = " ".join(
        value.split()
    ).strip()

    return normalized or None


def _text_list(
    value: Any,
) -> list[str]:
    """Normaliseer een lijst met teksten."""

    if not isinstance(
        value,
        list,
    ):
        return []

    result: list[str] = []
    seen: set[str] = set()

    for item in value:
        normalized = (
            _optional_text(
                item
            )
        )

        if normalized is None:
            continue

        comparison = (
            normalized.casefold()
        )

        if comparison in seen:
            continue

        seen.add(
            comparison
        )

        result.append(
            normalized
        )

    return result


def build_classification_input(
    opportunity: dict[str, Any],
) -> OpportunityClassificationInput:
    """Maak classificatie-input uit structured opportunity."""

    title = _optional_text(
        opportunity.get(
            "title"
        )
    )

    if title is None:
        raise ValueError(
            "De structured opportunity "
            "heeft geen geldige titel."
        )

    minimum_years_experience = (
        opportunity.get(
            "minimum_years_experience"
        )
    )

    return OpportunityClassificationInput(
        title=title,
        client_name=_optional_text(
            opportunity.get(
                "client_name"
            )
        ),
        description=_optional_text(
            opportunity.get(
                "description"
            )
        ),
        education_level=_optional_text(
            opportunity.get(
                "education_level"
            )
        ),
        minimum_years_experience=(
            minimum_years_experience
        ),
        requirements=_text_list(
            opportunity.get(
                "requirements"
            )
        ),
        wishes=_text_list(
            opportunity.get(
                "wishes"
            )
        ),
        competencies=_text_list(
            opportunity.get(
                "competencies"
            )
        ),
        skills=_text_list(
            opportunity.get(
                "skills"
            )
        ),
    )


def render_classification_input(
    classification_input: OpportunityClassificationInput,
) -> str:
    """Render stabiele JSON-input voor OpenAI en hashing."""

    payload = (
        classification_input
        .model_dump(
            mode="json",
            exclude_none=True,
        )
    )

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )