"""Tests voor kandidaatprofiel-input en evidenceverificatie."""

import pytest

from backend.app.schemas.candidate_profile import (
    CandidateProfile,
    EvidenceBackedNarrative,
    EvidenceBackedText,
    WorkExperience,
)
from backend.app.services.candidate_cv_text import (
    ExtractedCvText,
)
from backend.app.services.candidate_profile_input import (
    MAX_CANDIDATE_PROFILE_INPUT_CHARACTERS,
    CandidateProfileInputTooLargeError,
    evidence_exists_in_source,
    iter_evidence_snippets,
    prepare_candidate_profile_input,
    verify_candidate_profile_evidence,
)


def extracted_text(
    value: str,
) -> ExtractedCvText:
    """Maak eenvoudige uitgelezen CV-tekst."""

    return ExtractedCvText(
        text=value,
        source_type="pdf",
        page_count=2,
        character_count=len(
            value.replace(
                " ",
                ""
            )
        ),
    )


def test_prepared_input_has_stable_hash() -> None:
    first = prepare_candidate_profile_input(
        extracted_text(
            (
                "Robert Cooper\n\n"
                "Data Engineer met ervaring "
                "in Python en SQL voor "
                "publieke organisaties."
            )
        )
    )

    second = prepare_candidate_profile_input(
        extracted_text(
            (
                "  Robert   Cooper\r\n"
                "\r\n"
                "Data Engineer met ervaring "
                "in Python en SQL voor "
                "publieke organisaties. "
            )
        )
    )

    assert (
        first.text
        == second.text
    )

    assert (
        first.input_sha256
        == second.input_sha256
    )

def test_changed_input_changes_hash() -> None:
    first = prepare_candidate_profile_input(
        extracted_text(
            (
                "Robert Cooper werkt als "
                "Data Engineer met Python en SQL "
                "voor publieke organisaties."
            )
        )
    )

    second = prepare_candidate_profile_input(
        extracted_text(
            (
                "Robert Cooper werkt als "
                "Data Engineer met Python en Azure "
                "voor publieke organisaties."
            )
        )
    )

    assert (
        first.input_sha256
        != second.input_sha256
    )

def test_unsafe_control_characters_are_removed() -> None:
    result = prepare_candidate_profile_input(
        extracted_text(
            (
                "Robert Cooper\x00\n"
                "Data Engineer met Python "
                "en SQL voor publieke organisaties."
            )
        )
    )

    assert "\x00" not in result.text

    assert (
        "Robert Cooper"
        in result.text
    )


def test_oversized_input_is_rejected() -> None:
    value = (
        "A"
        * (
            MAX_CANDIDATE_PROFILE_INPUT_CHARACTERS
            + 1
        )
    )

    with pytest.raises(
        CandidateProfileInputTooLargeError
    ):
        prepare_candidate_profile_input(
            extracted_text(
                value
            )
        )


def test_evidence_matches_case_and_whitespace_normalized_source() -> None:
    source_text = (
        "Data Engineer\n"
        "Ervaring met   Python en SQL."
    )

    assert evidence_exists_in_source(
        source_text=source_text,
        evidence_text=(
            "ervaring met Python en SQL."
        ),
    )


def test_invented_evidence_does_not_match_source() -> None:
    source_text = (
        "Ervaring met Python en SQL."
    )

    assert not evidence_exists_in_source(
        source_text=source_text,
        evidence_text=(
            "Tien jaar ervaring met Python en SQL."
        ),
    )


def test_nested_profile_evidence_is_collected() -> None:
    profile = CandidateProfile(
        full_name=EvidenceBackedText(
            value="Robert Cooper",
            evidence=[
                {
                    "text": (
                        "Robert Cooper"
                    ),
                }
            ],
        ),

        work_experience=[
            WorkExperience(
                job_title=(
                    "Data Engineer"
                ),
                organization=(
                    "Organisatie X"
                ),
                description=(
                    "Ontwikkeling van "
                    "dataplatformen."
                ),
                evidence=[
                    {
                        "text": (
                            "Data Engineer "
                            "Organisatie X"
                        ),
                    },
                    {
                        "text": (
                            "Ontwikkeling van "
                            "dataplatformen"
                        ),
                    },
                ],
            )
        ],
    )

    snippets = list(
        iter_evidence_snippets(
            profile
        )
    )

    assert [
        snippet.text
        for snippet in snippets
    ] == [
        "Robert Cooper",
        "Data Engineer Organisatie X",
        "Ontwikkeling van dataplatformen",
    ]


def test_complete_profile_evidence_verifies() -> None:
    source_text = """
    Robert Cooper

    Data Engineer bij Organisatie X

    Ontwikkeling van dataplatformen met
    Python en SQL.
    """

    profile = CandidateProfile(
        full_name=EvidenceBackedText(
            value="Robert Cooper",
            evidence=[
                {
                    "text":
                        "Robert Cooper",
                }
            ],
        ),

        profile_summary=(
            EvidenceBackedNarrative(
                value=(
                    "Data Engineer met "
                    "ervaring in dataplatformen."
                ),
                evidence=[
                    {
                        "text": (
                            "Data Engineer "
                            "bij Organisatie X"
                        ),
                    },
                    {
                        "text": (
                            "Ontwikkeling van "
                            "dataplatformen"
                        ),
                    },
                ],
            )
        ),

        skills=[
            EvidenceBackedText(
                value="Python",
                evidence=[
                    {
                        "text": (
                            "Python en SQL"
                        ),
                    }
                ],
            )
        ],
    )

    result = (
        verify_candidate_profile_evidence(
            profile=profile,
            source_text=source_text,
        )
    )

    assert result.is_valid is True

    assert (
        result.total_snippets
        == 4
    )

    assert (
        result.verified_snippets
        == 4
    )

    assert (
        result.missing_snippets
        == ()
    )


def test_profile_with_invented_evidence_fails_verification() -> None:
    source_text = """
    Robert Cooper

    Data Engineer met ervaring in
    Python en SQL.
    """

    profile = CandidateProfile(
        skills=[
            EvidenceBackedText(
                value="Kubernetes",
                evidence=[
                    {
                        "text": (
                            "Expert in Kubernetes"
                        ),
                    }
                ],
            )
        ]
    )

    result = (
        verify_candidate_profile_evidence(
            profile=profile,
            source_text=source_text,
        )
    )

    assert result.is_valid is False

    assert (
        result.total_snippets
        == 1
    )

    assert (
        result.verified_snippets
        == 0
    )

    assert (
        result.missing_snippets
        == (
            "Expert in Kubernetes",
        )
    )