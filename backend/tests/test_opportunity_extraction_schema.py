"""Tests voor het gestructureerde extractieschema."""

from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.schemas.opportunity_extraction import (
    ExtractedOpportunity,
    OpportunityExtractionEnvelope,
)


def test_valid_extracted_opportunity() -> None:
    """Een realistische opdracht wordt geaccepteerd."""

    result = ExtractedOpportunity(
        title="Senior Projectleider",
        client_name="Gemeente Voorbeeld",
        start_date=date(
            2026,
            8,
            1,
        ),
        end_date=date(
            2027,
            1,
            31,
        ),
        hours_per_week_min=32,
        hours_per_week_max=36,
        rate_max=125,
        rate_period="hour",
        requirements=[
            "Minimaal vijf jaar ervaring",
            "Minimaal vijf jaar ervaring",
            "",
        ],
        work_arrangement="hybrid",
    )

    assert result.title == (
        "Senior Projectleider"
    )

    assert result.requirements == [
        "Minimaal vijf jaar ervaring"
    ]

    assert result.rate_currency == "EUR"


def test_rejects_invalid_date_range() -> None:
    """Een einddatum vóór de startdatum is ongeldig."""

    with pytest.raises(
        ValidationError
    ):
        ExtractedOpportunity(
            title="Projectleider",
            start_date=date(
                2026,
                9,
                1,
            ),
            end_date=date(
                2026,
                8,
                1,
            ),
        )


def test_rejects_invalid_hours_range() -> None:
    """Het maximumaantal uren mag niet lager zijn."""

    with pytest.raises(
        ValidationError
    ):
        ExtractedOpportunity(
            title="Adviseur",
            hours_per_week_min=36,
            hours_per_week_max=24,
        )


def test_valid_extraction_envelope() -> None:
    """Confidence en reviewinformatie worden gevalideerd."""

    result = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Data Engineer",
        ),
        overall_confidence=0.93,
        review_reasons=[],
    )

    assert result.overall_confidence == 0.93
    assert result.review_reasons == []
