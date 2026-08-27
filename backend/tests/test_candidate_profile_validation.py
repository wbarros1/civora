"""Tests voor deterministische kandidaatprofielvalidatie."""

from backend.app.schemas.candidate_profile import (
    CandidateProfile,
    CandidateProfileExtractionEnvelope,
    EvidenceBackedNarrative,
    EvidenceBackedText,
    WorkExperience,
)
from backend.app.services.candidate_profile_extractor import (
    CandidateProfileExtractionResult,
)
from backend.app.services.candidate_profile_input import (
    PreparedCandidateProfileInput,
)
from backend.app.services.candidate_profile_validation import (
    validate_candidate_profile_extraction,
)


SOURCE_TEXT = """
Robert Cooper

Data Engineer

Data Engineer bij Organisatie X

Ontwikkeling van dataplatformen met Python en SQL.

Technologieën: Python, SQL, Azure.

Nederlands - moedertaal
Engels - professioneel
""".strip()


def prepared_input(
    *,
    text: str = SOURCE_TEXT,
    sha256: str = (
        "a" * 64
    ),
) -> PreparedCandidateProfileInput:
    """Maak testinput."""

    return PreparedCandidateProfileInput(
        text=text,
        input_sha256=sha256,
        character_count=len(
            text
        ),
        readable_character_count=len(
            "".join(
                text.split()
            )
        ),
        line_count=len(
            text.splitlines()
        ),
        source_type="pdf",
        page_count=2,
    )


def extraction_result(
    *,
    profile: CandidateProfile,
    confidence: float = 0.85,
    review_reasons: (
        list[str]
        | None
    ) = None,
    input_sha256: str = (
        "a" * 64
    ),
) -> CandidateProfileExtractionResult:
    """Maak een LLM-resultaat zonder API-call."""

    return CandidateProfileExtractionResult(
        extraction=(
            CandidateProfileExtractionEnvelope(
                profile=profile,
                overall_confidence=confidence,
                review_reasons=(
                    review_reasons
                    or []
                ),
            )
        ),
        response_id="resp_test",
        model_name="test-model",
        prompt_version=(
            "candidate-profile-v1"
        ),
        input_sha256=input_sha256,
        input_tokens=100,
        output_tokens=100,
        total_tokens=200,
    )


def valid_profile() -> CandidateProfile:
    """Maak een profiel met verifieerbare claims."""

    return CandidateProfile(
        full_name=(
            EvidenceBackedText(
                value="Robert Cooper",
                evidence=[
                    {
                        "text":
                            "Robert Cooper",
                    }
                ],
            )
        ),

        headline=(
            EvidenceBackedText(
                value="Data Engineer",
                evidence=[
                    {
                        "text":
                            "Data Engineer",
                    }
                ],
            )
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
                    "Werkt aan "
                    "dataplatformen."
                ),
                technologies=[
                    "Python",
                    "SQL",
                ],
                evidence=[
                    {
                        "text": (
                            "Data Engineer bij "
                            "Organisatie X"
                        ),
                    },
                    {
                        "text": (
                            "Ontwikkeling van "
                            "dataplatformen met "
                            "Python en SQL."
                        ),
                    },
                ],
            )
        ],

        skills=[
            EvidenceBackedText(
                value="Python",
                evidence=[
                    {
                        "text":
                            "Python en SQL",
                    }
                ],
            )
        ],
    )


def test_valid_profile_passes_validation() -> None:
    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=valid_profile()
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is True
    assert result.requires_review is False

    assert (
        result.total_evidence_snippets
        == result.verified_evidence_snippets
    )

    assert (
        result.atomic_claims_checked
        == result.atomic_claims_verified
    )


def test_input_hash_mismatch_is_blocking() -> None:
    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=valid_profile(),
                    input_sha256=(
                        "b" * 64
                    ),
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is False

    assert (
        "input_hash_mismatch"
        in {
            issue.code
            for issue in result.errors
        }
    )


def test_missing_evidence_is_blocking() -> None:
    profile = CandidateProfile(
        skills=[
            EvidenceBackedText(
                value="Kubernetes",
                evidence=[
                    {
                        "text":
                            "Expert in Kubernetes",
                    }
                ],
            )
        ]
    )

    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=profile
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is False

    assert (
        "unverified_evidence"
        in {
            issue.code
            for issue in result.errors
        }
    )


def test_atomic_claim_must_exist_in_evidence() -> None:
    profile = CandidateProfile(
        skills=[
            EvidenceBackedText(
                value="Azure",
                evidence=[
                    {
                        "text":
                            "Python en SQL",
                    }
                ],
            )
        ]
    )

    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=profile
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is False

    assert (
        "atomic_value_not_supported_by_evidence"
        in {
            issue.code
            for issue in result.errors
        }
    )


def test_atomic_claim_must_exist_in_source() -> None:
    profile = CandidateProfile(
        skills=[
            EvidenceBackedText(
                value="Kubernetes",
                evidence=[
                    {
                        "text":
                            "Python en SQL",
                    }
                ],
            )
        ]
    )

    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=profile
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is False

    assert (
        "atomic_value_not_in_source"
        in {
            issue.code
            for issue in result.errors
        }
    )


def test_empty_profile_is_blocking() -> None:
    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=(
                        CandidateProfile()
                    )
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is False

    assert (
        "empty_candidate_profile"
        in {
            issue.code
            for issue in result.errors
        }
    )


def test_low_confidence_requires_review() -> None:
    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=valid_profile(),
                    confidence=0.55,
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is True
    assert result.requires_review is True

    assert (
        "low_confidence"
        in {
            issue.code
            for issue in result.review_issues
        }
    )


def test_llm_review_reason_requires_review() -> None:
    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=valid_profile(),
                    review_reasons=[
                        (
                            "Datums van één functie "
                            "zijn onduidelijk."
                        )
                    ],
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is True
    assert result.requires_review is True

    assert (
        "llm_review_reason"
        in {
            issue.code
            for issue in result.review_issues
        }
    )


def test_narrative_paraphrase_is_allowed_with_real_evidence() -> None:
    profile = valid_profile()

    profile.profile_summary = (
        EvidenceBackedNarrative(
            value=(
                "Data Engineer met ervaring "
                "in de ontwikkeling van "
                "dataplatformen."
            ),
            evidence=[
                {
                    "text": (
                        "Data Engineer bij "
                        "Organisatie X"
                    ),
                },
                {
                    "text": (
                        "Ontwikkeling van "
                        "dataplatformen met "
                        "Python en SQL."
                    ),
                },
            ],
        )
    )

    result = (
        validate_candidate_profile_extraction(
            extraction_result=(
                extraction_result(
                    profile=profile
                )
            ),
            prepared_input=(
                prepared_input()
            ),
        )
    )

    assert result.is_valid is True