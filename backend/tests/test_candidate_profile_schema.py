"""Tests voor het gestructureerde kandidaatprofiel."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.candidate_profile import (
    CandidateDate,
    CandidateProfile,
    CandidateProfileExtractionEnvelope,
    EvidenceBackedNarrative,
    EvidenceBackedText,
    WorkExperience,
)


def evidence(
    text: str,
) -> list[dict[str, str]]:
    """Maak eenvoudig bewijs voor tests."""

    return [
        {
            "text": text,
        }
    ]


def test_evidence_is_normalized_and_deduplicated() -> None:
    value = EvidenceBackedText(
        value="  Python   ontwikkeling  ",
        evidence=[
            {
                "text": (
                    "Ontwikkeling met Python"
                ),
            },
            {
                "text": (
                    "  Ontwikkeling   met Python "
                ),
            },
        ],
    )

    assert (
        value.value
        == "Python ontwikkeling"
    )

    assert (
        len(value.evidence)
        == 1
    )

    assert (
        value.evidence[0].text
        == "Ontwikkeling met Python"
    )


def test_current_work_experience_cannot_have_end_date() -> None:
    with pytest.raises(
        ValidationError
    ):
        WorkExperience(
            job_title="Data Engineer",
            organization="Organisatie X",
            start_date=CandidateDate(
                year=2022,
                month=1,
            ),
            end_date=CandidateDate(
                year=2025,
                month=1,
            ),
            is_current=True,
            evidence=evidence(
                "Data Engineer bij Organisatie X"
            ),
        )


def test_invalid_work_experience_date_range_is_rejected() -> None:
    with pytest.raises(
        ValidationError
    ):
        WorkExperience(
            job_title="Consultant",
            start_date=CandidateDate(
                year=2024,
                month=6,
            ),
            end_date=CandidateDate(
                year=2023,
                month=12,
            ),
            evidence=evidence(
                "Consultant 2024 - 2023"
            ),
        )


def test_empty_work_experience_is_rejected() -> None:
    with pytest.raises(
        ValidationError
    ):
        WorkExperience(
            evidence=evidence(
                "Onvolledige werkervaring"
            ),
        )


def test_candidate_terms_are_deduplicated() -> None:
    profile = CandidateProfile(
        skills=[
            EvidenceBackedText(
                value="Python",
                evidence=evidence(
                    "Python"
                ),
            ),
            EvidenceBackedText(
                value="python",
                evidence=evidence(
                    "Python ontwikkeling"
                ),
            ),
            EvidenceBackedText(
                value="SQL",
                evidence=evidence(
                    "SQL"
                ),
            ),
        ]
    )

    assert (
        len(profile.skills)
        == 2
    )

    assert [
        item.value
        for item in profile.skills
    ] == [
        "Python",
        "SQL",
    ]


def test_profile_summary_requires_evidence() -> None:
    with pytest.raises(
        ValidationError
    ):
        EvidenceBackedNarrative(
            value=(
                "Ervaren data-specialist."
            ),
            evidence=[],
        )


def test_extraction_envelope_normalizes_review_reasons() -> None:
    envelope = (
        CandidateProfileExtractionEnvelope(
            profile=CandidateProfile(),
            overall_confidence=0.8,
            review_reasons=[
                (
                    "  Datum van functie "
                    "is onduidelijk "
                ),
                (
                    "Datum van functie "
                    "is onduidelijk"
                ),
                "Certificaatdatum ontbreekt",
            ],
        )
    )

    assert (
        envelope.review_reasons
        == [
            (
                "Datum van functie "
                "is onduidelijk"
            ),
            "Certificaatdatum ontbreekt",
        ]
    )