"""Tests voor kandidaatprofiel-persistence en lifecycle."""

import pytest

from backend.app.schemas.candidate_profile import (
    CandidateProfile,
    CandidateProfileExtractionEnvelope,
    EvidenceBackedText,
)
from backend.app.services.candidate_cv_text import (
    ExtractedCvText,
)
from backend.app.services.candidate_profile_extractor import (
    CandidateProfileExtractionResult,
)
from backend.app.services.candidate_profile_input import (
    PreparedCandidateProfileInput,
)
from backend.app.services.candidate_profile_processing import (
    CANDIDATE_PROFILE_SCHEMA_VERSION,
    CandidateProfileNotFoundError,
    CandidateProfileValidationFailedError,
    process_user_cv_candidate_profile,
)
from backend.app.services.candidate_profile_validation import (
    CandidateProfileValidationIssue,
    CandidateProfileValidationResult,
)


USER_ID = "user-test"
CV_ID = "cv-test"

INPUT_HASH = (
    "a" * 64
)


def cv_record() -> dict:
    """Maak een eenvoudig CV-record."""

    return {
        "id": CV_ID,
        "user_id": USER_ID,
        "storage_path": (
            "user-test/cv-test/source.pdf"
        ),
        "mime_type": "application/pdf",
        "processing_status": "uploaded",
    }


def extracted_text() -> ExtractedCvText:
    """Maak lokale CV-tekst."""

    text = (
        "Robert Cooper is Data Engineer "
        "met ervaring in Python en SQL."
    )

    return ExtractedCvText(
        text=text,
        source_type="pdf",
        page_count=2,
        character_count=50,
    )


def prepared_input() -> PreparedCandidateProfileInput:
    """Maak voorbereide input."""

    text = (
        "Robert Cooper is Data Engineer "
        "met ervaring in Python en SQL."
    )

    return PreparedCandidateProfileInput(
        text=text,
        input_sha256=INPUT_HASH,
        character_count=len(
            text
        ),
        readable_character_count=50,
        line_count=1,
        source_type="pdf",
        page_count=2,
    )


def llm_result() -> CandidateProfileExtractionResult:
    """Maak geldige LLM-output."""

    profile = CandidateProfile(
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
        )
    )

    return CandidateProfileExtractionResult(
        extraction=(
            CandidateProfileExtractionEnvelope(
                profile=profile,
                overall_confidence=0.85,
                review_reasons=[],
            )
        ),
        response_id="resp_test",
        model_name="test-model",
        prompt_version=(
            "candidate-profile-v1"
        ),
        input_sha256=INPUT_HASH,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )


def valid_validation(
    *,
    review: bool = False,
) -> CandidateProfileValidationResult:
    """Maak geldige validation output."""

    issues = ()

    if review:
        issues = (
            CandidateProfileValidationIssue(
                code="low_confidence",
                severity="review",
                path="overall_confidence",
                message="Review nodig.",
            ),
        )

    return CandidateProfileValidationResult(
        issues=issues,
        total_evidence_snippets=1,
        verified_evidence_snippets=1,
        atomic_claims_checked=1,
        atomic_claims_verified=1,
    )


def configure_common_mocks(
    monkeypatch,
):
    """Mock de pre-LLM pipeline."""

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_user_cv"
        ),
        lambda **_: cv_record(),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "download_user_cv_file"
        ),
        lambda **_: b"pdf-bytes",
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "extract_cv_text"
        ),
        lambda **_: extracted_text(),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "prepare_candidate_profile_input"
        ),
        lambda _: prepared_input(),
    )


def test_processing_creates_profile_and_marks_ready(
    monkeypatch,
) -> None:
    configure_common_mocks(
        monkeypatch
    )

    statuses = []

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "update_user_cv_processing_status"
        ),
        lambda **kwargs: statuses.append(
            kwargs
        ),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_candidate_profile_by_cv"
        ),
        lambda **_: None,
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "extract_candidate_profile_with_llm"
        ),
        lambda _: llm_result(),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "validate_candidate_profile_extraction"
        ),
        lambda **_: valid_validation(),
    )

    saved_payload = {}

    def fake_upsert(
        **kwargs,
    ):
        saved_payload.update(
            kwargs
        )

        return {
            "id": "profile-test",
            **kwargs,
        }

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "upsert_candidate_profile"
        ),
        fake_upsert,
    )

    result = (
        process_user_cv_candidate_profile(
            user_id=USER_ID,
            cv_id=CV_ID,
        )
    )

    assert result.outcome == "created"

    assert [
        item["status"]
        for item in statuses
    ] == [
        "processing",
        "ready",
    ]

    assert (
        saved_payload["input_hash"]
        == INPUT_HASH
    )

    assert (
        saved_payload["schema_version"]
        == CANDIDATE_PROFILE_SCHEMA_VERSION
    )

    assert (
        saved_payload["provider"]
        == "openai"
    )


def test_current_profile_is_skipped_without_llm(
    monkeypatch,
) -> None:
    configure_common_mocks(
        monkeypatch
    )

    statuses = []

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "update_user_cv_processing_status"
        ),
        lambda **kwargs: statuses.append(
            kwargs
        ),
    )

    existing = {
        "id": "profile-existing",
        "schema_version": (
            CANDIDATE_PROFILE_SCHEMA_VERSION
        ),
        "prompt_version": (
            "candidate-profile-v1"
        ),
        "input_hash": INPUT_HASH,
        "validation_errors": [],
    }

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_candidate_profile_by_cv"
        ),
        lambda **_: existing,
    )

    def fail_if_called(
        _,
    ):
        raise AssertionError(
            "LLM mag niet worden aangeroepen."
        )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "extract_candidate_profile_with_llm"
        ),
        fail_if_called,
    )

    result = (
        process_user_cv_candidate_profile(
            user_id=USER_ID,
            cv_id=CV_ID,
        )
    )

    assert result.outcome == "skipped"

    assert [
        item["status"]
        for item in statuses
    ] == [
        "processing",
        "ready",
    ]


def test_valid_review_profile_is_stored_and_ready(
    monkeypatch,
) -> None:
    configure_common_mocks(
        monkeypatch
    )

    statuses = []

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "update_user_cv_processing_status"
        ),
        lambda **kwargs: statuses.append(
            kwargs
        ),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_candidate_profile_by_cv"
        ),
        lambda **_: None,
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "extract_candidate_profile_with_llm"
        ),
        lambda _: llm_result(),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "validate_candidate_profile_extraction"
        ),
        lambda **_: valid_validation(
            review=True
        ),
    )

    stored_payload = {}

    def fake_upsert(
        **kwargs,
    ):
        stored_payload.update(
            kwargs
        )

        return {
            "id": "profile-test",
            **kwargs,
        }

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "upsert_candidate_profile"
        ),
        fake_upsert,
    )

    result = (
        process_user_cv_candidate_profile(
            user_id=USER_ID,
            cv_id=CV_ID,
        )
    )

    assert result.requires_review is True

    assert (
        stored_payload[
            "validation_errors"
        ][0]["severity"]
        == "review"
    )

    assert (
        statuses[-1]["status"]
        == "ready"
    )


def test_invalid_profile_is_not_stored_and_marks_failed(
    monkeypatch,
) -> None:
    configure_common_mocks(
        monkeypatch
    )

    statuses = []

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "update_user_cv_processing_status"
        ),
        lambda **kwargs: statuses.append(
            kwargs
        ),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_candidate_profile_by_cv"
        ),
        lambda **_: None,
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "extract_candidate_profile_with_llm"
        ),
        lambda _: llm_result(),
    )

    invalid_validation = (
        CandidateProfileValidationResult(
            issues=(
                CandidateProfileValidationIssue(
                    code=(
                        "unverified_evidence"
                    ),
                    severity="error",
                    path="profile",
                    message=(
                        "Evidence ongeldig."
                    ),
                ),
            ),
            total_evidence_snippets=1,
            verified_evidence_snippets=0,
            atomic_claims_checked=1,
            atomic_claims_verified=0,
        )
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "validate_candidate_profile_extraction"
        ),
        lambda **_: (
            invalid_validation
        ),
    )

    def fail_if_stored(
        **_,
    ):
        raise AssertionError(
            "Ongeldig profiel mag "
            "niet worden opgeslagen."
        )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "upsert_candidate_profile"
        ),
        fail_if_stored,
    )

    with pytest.raises(
        CandidateProfileValidationFailedError
    ):
        process_user_cv_candidate_profile(
            user_id=USER_ID,
            cv_id=CV_ID,
        )

    assert [
        item["status"]
        for item in statuses
    ] == [
        "processing",
        "failed",
    ]

    assert (
        statuses[-1][
            "processing_error"
        ]
        == (
            "Het kandidaatprofiel kon niet "
            "betrouwbaar worden gevalideerd."
        )
    )


def test_unexpected_error_does_not_store_sensitive_message(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_user_cv"
        ),
        lambda **_: cv_record(),
    )

    statuses = []

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "update_user_cv_processing_status"
        ),
        lambda **kwargs: statuses.append(
            kwargs
        ),
    )

    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "download_user_cv_file"
        ),
        lambda **_: (
            (_ for _ in ()).throw(
                RuntimeError(
                    "GEHEIME CV-INHOUD"
                )
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="GEHEIME CV-INHOUD",
    ):
        process_user_cv_candidate_profile(
            user_id=USER_ID,
            cv_id=CV_ID,
        )

    assert (
        statuses[-1]["status"]
        == "failed"
    )

    assert (
        "GEHEIME CV-INHOUD"
        not in (
            statuses[-1][
                "processing_error"
            ]
        )
    )

    assert (
        statuses[-1][
            "processing_error"
        ]
        == (
            "Automatische CV-verwerking "
            "is mislukt."
        )
    )


def test_missing_cv_is_rejected_before_processing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        (
            "backend.app.services."
            "candidate_profile_processing."
            "get_user_cv"
        ),
        lambda **_: None,
    )

    with pytest.raises(
        CandidateProfileNotFoundError
    ):
        process_user_cv_candidate_profile(
            user_id=USER_ID,
            cv_id=CV_ID,
        )