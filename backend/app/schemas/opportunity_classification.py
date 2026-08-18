"""Pydantic-schema's voor Civora vakgroepclassificatie."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


Vakgroep = Literal[
    "procesmanagement",
    "data_ai",
    "ict",
    "finance",
]

OpportunityVakgroep = Literal[
    "procesmanagement",
    "data_ai",
    "ict",
    "finance",
    "overige",
]


class VakgroepScore(BaseModel):
    """LLM-score voor één Civora-vakgroep."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    relevance_score: int = Field(
        ge=0,
        le=100,
    )

    reason: str = Field(
        min_length=1,
        max_length=400,
    )

    @field_validator(
        "reason"
    )
    @classmethod
    def normalize_reason(
        cls,
        value: str,
    ) -> str:
        """Normaliseer de korte motivatie."""

        return " ".join(
            value.split()
        ).strip()


class OpportunityClassificationEnvelope(
    BaseModel
):
    """Ruwe gestructureerde output van de classifier."""

    model_config = ConfigDict(
        extra="forbid",
    )

    procesmanagement: VakgroepScore
    data_ai: VakgroepScore
    ict: VakgroepScore
    finance: VakgroepScore

    classification_confidence: float = Field(
        ge=0,
        le=1,
    )

    review_reasons: list[str] = Field(
        default_factory=list,
        max_length=4,
    )

    @field_validator(
        "review_reasons"
    )
    @classmethod
    def normalize_review_reasons(
        cls,
        values: list[str],
    ) -> list[str]:
        """Normaliseer en dedupliceer reviewredenen."""

        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = " ".join(
                value.split()
            ).strip()

            if not cleaned:
                continue

            comparison = (
                cleaned.casefold()
            )

            if comparison in seen:
                continue

            seen.add(
                comparison
            )

            normalized.append(
                cleaned
            )

        return normalized