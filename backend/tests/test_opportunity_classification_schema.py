"""Tests voor het classificatieschema."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.opportunity_classification import (
    OpportunityClassificationEnvelope,
)


def valid_payload() -> dict:
    """Maak een geldige classifier-output."""

    return {
        "procesmanagement": {
            "relevance_score": 88,
            "reason": (
                "De opdracht bevat "
                "projectmanagement."
            ),
        },
        "data_ai": {
            "relevance_score": 74,
            "reason": (
                "Dataplatformen zijn "
                "inhoudelijk relevant."
            ),
        },
        "ict": {
            "relevance_score": 52,
            "reason": (
                "Er is een beperkte "
                "technische component."
            ),
        },
        "finance": {
            "relevance_score": 8,
            "reason": (
                "Financiële werkzaamheden "
                "vormen geen kernonderdeel."
            ),
        },
        "classification_confidence": 0.91,
        "review_reasons": [],
    }


def test_valid_classification() -> None:
    """Vier geldige scores worden geaccepteerd."""

    classification = (
        OpportunityClassificationEnvelope(
            **valid_payload()
        )
    )

    assert (
        classification
        .procesmanagement
        .relevance_score
        == 88
    )

    assert (
        classification
        .classification_confidence
        == 0.91
    )


def test_rejects_score_above_100() -> None:
    """Een score boven 100 wordt geweigerd."""

    payload = valid_payload()

    payload[
        "procesmanagement"
    ][
        "relevance_score"
    ] = 101

    with pytest.raises(
        ValidationError
    ):
        OpportunityClassificationEnvelope(
            **payload
        )


def test_rejects_missing_vakgroep() -> None:
    """Alle vier vakgroepen zijn verplicht."""

    payload = valid_payload()

    del payload["finance"]

    with pytest.raises(
        ValidationError
    ):
        OpportunityClassificationEnvelope(
            **payload
        )