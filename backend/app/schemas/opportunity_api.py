"""API-schema's voor gestructureerde opdrachten."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class OpportunityListItem(BaseModel):
    """Compacte opdracht voor de zoekresultaten."""

    id: str
    source_reference: str

    title: str
    client_name: str | None = None

    location: str | None = None
    province: str | None = None
    work_arrangement: str = "unknown"

    start_date: date | None = None
    end_date: date | None = None
    application_deadline: datetime | None = None

    hours_per_week_min: float | None = None
    hours_per_week_max: float | None = None

    rate_min: float | None = None
    rate_max: float | None = None
    rate_currency: str | None = None
    rate_period: str | None = None

    employment_relationship: str = "unknown"

    source_status: str
    application_status: str


class OpportunityListResponse(BaseModel):
    """Gepagineerde lijst met opdrachten."""

    items: list[OpportunityListItem]

    limit: int
    offset: int
    has_more: bool


class OpportunityDetail(OpportunityListItem):
    """Volledige opdracht voor de detailpagina."""

    description: str | None = None

    publication_date: date | None = None

    duration_months: float | None = None
    extension_possible: bool | None = None
    number_of_positions: int | None = None

    education_level: str | None = None
    minimum_years_experience: float | None = None

    requirements: list[str] = []
    wishes: list[str] = []
    competencies: list[str] = []
    skills: list[str] = []

    contact_information: dict[str, Any] = {}

    extraction_confidence: float | None = None