"""Pydantic-schema's voor gestructureerde opdrachtextractie."""

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


WorkArrangement = Literal[
    "on_site",
    "hybrid",
    "remote",
    "unknown",
]

RatePeriod = Literal[
    "hour",
    "day",
    "month",
    "fixed",
    "unknown",
]

EmploymentRelationship = Literal[
    "zzp",
    "secondment",
    "both",
    "unknown",
]


class ContactInformation(BaseModel):
    """Contactgegevens die expliciet in de opdracht staan."""

    model_config = ConfigDict(
        extra="forbid",
    )

    name: str | None = None
    email: str | None = None
    phone: str | None = None


class ExtractedOpportunity(BaseModel):
    """Gestructureerde inhoud van één publieke inhuuropdracht."""

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

    location: str | None = Field(
        default=None,
        max_length=500,
    )

    province: str | None = Field(
        default=None,
        max_length=200,
    )

    work_arrangement: WorkArrangement = (
        "unknown"
    )

    start_date: date | None = None
    end_date: date | None = None
    application_deadline: datetime | None = None
    publication_date: date | None = None

    hours_per_week_min: float | None = Field(
        default=None,
        ge=0,
        le=168,
    )

    hours_per_week_max: float | None = Field(
        default=None,
        ge=0,
        le=168,
    )

    duration_months: float | None = Field(
        default=None,
        ge=0,
        le=120,
    )

    extension_possible: bool | None = None

    number_of_positions: int | None = Field(
        default=None,
        ge=1,
        le=1000,
    )

    rate_min: float | None = Field(
        default=None,
        ge=0,
    )

    rate_max: float | None = Field(
        default=None,
        ge=0,
    )

    rate_currency: str = Field(
        default="EUR",
        min_length=3,
        max_length=3,
    )

    rate_period: RatePeriod = "unknown"

    employment_relationship: (
        EmploymentRelationship
    ) = "unknown"

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

    contact_information: ContactInformation = (
        Field(
            default_factory=ContactInformation,
        )
    )


    @field_validator(
        "rate_currency"
    )
    @classmethod
    def normalize_currency(
        cls,
        value: str,
    ) -> str:
        """Normaliseer ISO-valutacodes naar hoofdletters."""

        return value.upper()

    @field_validator(
        "requirements",
        "wishes",
        "competencies",
        "skills",
    )
    @classmethod
    def normalize_text_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        """Verwijder lege en dubbele lijstwaarden."""

        normalized_values: list[str] = []
        seen_values: set[str] = set()

        for value in values:
            cleaned_value = " ".join(
                value.split()
            ).strip()

            if not cleaned_value:
                continue

            comparison_value = (
                cleaned_value.casefold()
            )

            if comparison_value in seen_values:
                continue

            seen_values.add(
                comparison_value
            )

            normalized_values.append(
                cleaned_value
            )

        return normalized_values

    @model_validator(
        mode="after"
    )
    def validate_ranges(
        self,
    ) -> "ExtractedOpportunity":
        """Controleer datum-, uren- en tariefranges."""

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError(
                "end_date mag niet vóór start_date liggen."
            )

        if (
            self.hours_per_week_min is not None
            and self.hours_per_week_max is not None
            and self.hours_per_week_max
            < self.hours_per_week_min
        ):
            raise ValueError(
                "hours_per_week_max mag niet lager zijn "
                "dan hours_per_week_min."
            )

        if (
            self.rate_min is not None
            and self.rate_max is not None
            and self.rate_max < self.rate_min
        ):
            raise ValueError(
                "rate_max mag niet lager zijn dan rate_min."
            )

        return self

class OpportunityExtractionEnvelope(
    BaseModel
):
    """Volledige gevalideerde output van één extractie."""

    model_config = ConfigDict(
        extra="forbid",
    )

    opportunity: ExtractedOpportunity

    overall_confidence: float = Field(
        ge=0,
        le=1,
    )

    review_reasons: list[str] = Field(
        default_factory=list,
        max_length=5,
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

        normalized_values: list[str] = []
        seen_values: set[str] = set()

        for value in values:
            cleaned_value = " ".join(
                value.split()
            ).strip()

            if not cleaned_value:
                continue

            comparison_value = (
                cleaned_value.casefold()
            )

            if comparison_value in seen_values:
                continue

            seen_values.add(
                comparison_value
            )

            normalized_values.append(
                cleaned_value
            )

        return normalized_values