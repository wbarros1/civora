"""Tests voor deterministische classificatieregels."""

from backend.app.schemas.opportunity_classification import (
    OpportunityClassificationEnvelope,
)
from backend.app.services.opportunity_classification_rules import (
    derive_classification,
)


def build_classification(
    *,
    procesmanagement: int,
    data_ai: int,
    ict: int,
    finance: int,
) -> OpportunityClassificationEnvelope:
    """Maak testclassificatie."""

    return OpportunityClassificationEnvelope(
        procesmanagement={
            "relevance_score":
                procesmanagement,
            "reason": "PM reden",
        },
        data_ai={
            "relevance_score":
                data_ai,
            "reason": "Data reden",
        },
        ict={
            "relevance_score":
                ict,
            "reason": "ICT reden",
        },
        finance={
            "relevance_score":
                finance,
            "reason": "Finance reden",
        },
        classification_confidence=0.9,
        review_reasons=[],
    )


def test_derives_multiple_matches() -> None:
    """Alle relevante vakgroepen worden gerangschikt."""

    decision = derive_classification(
        build_classification(
            procesmanagement=88,
            data_ai=74,
            ict=52,
            finance=8,
        )
    )

    assert (
        decision.primary_vakgroep
        == "procesmanagement"
    )

    assert [
        match.vakgroep
        for match
        in decision.matches
    ] == [
        "procesmanagement",
        "data_ai",
    ]


def test_uses_overige_below_threshold() -> None:
    """Geen score boven drempel resulteert in overige."""

    decision = derive_classification(
        build_classification(
            procesmanagement=59,
            data_ai=40,
            ict=25,
            finance=12,
        )
    )

    assert (
        decision.primary_vakgroep
        == "overige"
    )

    assert (
        decision.matches
        == ()
    )


def test_limits_matches_to_three() -> None:
    """Maximaal drie vakgroepen worden als match gebruikt."""

    decision = derive_classification(
        build_classification(
            procesmanagement=95,
            data_ai=90,
            ict=85,
            finance=80,
        )
    )

    assert len(
        decision.matches
    ) == 3

    assert [
        match.vakgroep
        for match
        in decision.matches
    ] == [
        "procesmanagement",
        "data_ai",
        "ict",
    ]


def test_threshold_is_inclusive() -> None:
    """Een score van exact 60 is relevant."""

    decision = derive_classification(
        build_classification(
            procesmanagement=60,
            data_ai=59,
            ict=10,
            finance=0,
        )
    )

    assert (
        decision.primary_vakgroep
        == "procesmanagement"
    )

    assert len(
        decision.matches
    ) == 1


def test_equal_top_score_adds_review_reason() -> None:
    """Gelijke hoogste scores blijven deterministisch."""

    decision = derive_classification(
        build_classification(
            procesmanagement=85,
            data_ai=85,
            ict=20,
            finance=5,
        )
    )

    assert (
        decision.primary_vakgroep
        == "procesmanagement"
    )

    assert any(
        "dezelfde hoogste"
        in reason
        for reason
        in decision.review_reasons
    )