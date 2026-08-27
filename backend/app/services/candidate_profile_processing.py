"""Verwerkingspipeline voor kandidaatprofielen uit basis-CV's."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from backend.app.repositories.candidate_profiles import (
    get_candidate_profile_by_cv,
    upsert_candidate_profile,
)
from backend.app.repositories.user_cvs import (
    get_user_cv,
    update_user_cv_processing_status,
)
from backend.app.services.candidate_cv_text import (
    CvTextExtractionError,
    UnreadableCvTextError,
    extract_cv_text,
)
from backend.app.services.candidate_profile_extractor import (
    PROMPT_VERSION,
    extract_candidate_profile_with_llm,
)
from backend.app.services.candidate_profile_input import (
    CandidateProfileInputError,
    prepare_candidate_profile_input,
)
from backend.app.services.candidate_profile_validation import (
    CandidateProfileValidationResult,
    validate_candidate_profile_extraction,
)
from backend.app.services.user_cv_files import (
    download_user_cv_file,
)


CANDIDATE_PROFILE_SCHEMA_VERSION = (
    "candidate-profile-v1"
)


CandidateProfileProcessingOutcome = Literal[
    "created",
    "updated",
    "skipped",
]


class CandidateProfileProcessingError(
    RuntimeError
):
    """Basisklasse voor kandidaatprofielverwerking."""


class CandidateProfileNotFoundError(
    CandidateProfileProcessingError
):
    """Het geselecteerde CV bestaat niet voor de gebruiker."""


class CandidateProfileValidationFailedError(
    CandidateProfileProcessingError
):
    """De LLM-output heeft de feitelijke validatie niet doorstaan."""

    def __init__(
        self,
        validation: (
            CandidateProfileValidationResult
        ),
    ) -> None:
        self.validation = validation

        super().__init__(
            "Het kandidaatprofiel kon niet "
            "betrouwbaar worden gevalideerd."
        )


@dataclass(
    frozen=True,
    slots=True,
)
class CandidateProfileProcessingResult:
    """Resultaat van één volledige CV-verwerking."""

    outcome: (
        CandidateProfileProcessingOutcome
    )

    user_cv_id: str

    candidate_profile: dict[
        str,
        Any
    ]

    requires_review: bool

    validation_issues: tuple[
        dict[str, Any],
        ...
    ]


def _serialize_validation_issues(
    validation: CandidateProfileValidationResult,
) -> list[
    dict[str, Any]
]:
    """Maak databaseveilige validation metadata."""

    return [
        {
            "code": issue.code,
            "severity": issue.severity,
            "path": issue.path,
            "message": issue.message,
        }
        for issue in validation.issues
    ]


def _stored_requires_review(
    candidate_profile: dict[
        str,
        Any
    ],
) -> bool:
    """Bepaal reviewstatus uit bestaande validatiemetadata."""

    issues = (
        candidate_profile.get(
            "validation_errors"
        )
        or []
    )

    return any(
        isinstance(
            issue,
            dict,
        )
        and issue.get(
            "severity"
        ) == "review"
        for issue in issues
    )


def _safe_processing_error(
    error: Exception,
) -> str:
    """
    Geef uitsluitend veilige foutinformatie
    terug voor opslag in user_cvs.

    CV-inhoud of OpenAI-output wordt nooit
    in processing_error opgeslagen.
    """

    if isinstance(
        error,
        UnreadableCvTextError,
    ):
        return (
            "Het CV bevat onvoldoende "
            "uitleesbare tekst."
        )

    if isinstance(
        error,
        CandidateProfileInputError,
    ):
        return (
            "Het CV kon niet veilig worden "
            "voorbereid voor verwerking."
        )

    if isinstance(
        error,
        CandidateProfileValidationFailedError,
    ):
        return (
            "Het kandidaatprofiel kon niet "
            "betrouwbaar worden gevalideerd."
        )

    if isinstance(
        error,
        CvTextExtractionError,
    ):
        return (
            "De tekst uit het CV kon niet "
            "worden uitgelezen."
        )

    return (
        "Automatische CV-verwerking is mislukt."
    )


def _is_existing_profile_current(
    *,
    candidate_profile: dict[
        str,
        Any
    ],
    input_hash: str,
) -> bool:
    """Controleer idempotency voor dezelfde CV-input."""

    return (
        candidate_profile.get(
            "schema_version"
        )
        == CANDIDATE_PROFILE_SCHEMA_VERSION

        and candidate_profile.get(
            "prompt_version"
        )
        == PROMPT_VERSION

        and candidate_profile.get(
            "input_hash"
        )
        == input_hash
    )


def process_user_cv_candidate_profile(
    *,
    user_id: str,
    cv_id: str,
) -> CandidateProfileProcessingResult:
    """
    Verwerk één eigen CV volledig tot
    een gevalideerd kandidaatprofiel.

    Alleen deterministisch geldige output
    wordt opgeslagen.
    """

    cv = get_user_cv(
        user_id=user_id,
        cv_id=cv_id,
    )

    if cv is None:
        raise CandidateProfileNotFoundError(
            "Het CV bestaat niet voor "
            "deze gebruiker."
        )

    update_user_cv_processing_status(
        user_id=user_id,
        cv_id=cv_id,
        status="processing",
        processing_error=None,
    )

    try:
        content = download_user_cv_file(
            storage_path=cv[
                "storage_path"
            ],
        )

        extracted_text = extract_cv_text(
            content=content,
            mime_type=cv[
                "mime_type"
            ],
        )

        prepared_input = (
            prepare_candidate_profile_input(
                extracted_text
            )
        )

        existing_profile = (
            get_candidate_profile_by_cv(
                user_id=user_id,
                user_cv_id=cv_id,
            )
        )

        if (
            existing_profile is not None
            and _is_existing_profile_current(
                candidate_profile=(
                    existing_profile
                ),
                input_hash=(
                    prepared_input
                    .input_sha256
                ),
            )
        ):
            update_user_cv_processing_status(
                user_id=user_id,
                cv_id=cv_id,
                status="ready",
                processing_error=None,
            )

            stored_issues = tuple(
                issue
                for issue in (
                    existing_profile.get(
                        "validation_errors"
                    )
                    or []
                )
                if isinstance(
                    issue,
                    dict,
                )
            )

            return (
                CandidateProfileProcessingResult(
                    outcome="skipped",
                    user_cv_id=cv_id,
                    candidate_profile=(
                        existing_profile
                    ),
                    requires_review=(
                        _stored_requires_review(
                            existing_profile
                        )
                    ),
                    validation_issues=(
                        stored_issues
                    ),
                )
            )

        extraction_result = (
            extract_candidate_profile_with_llm(
                prepared_input
            )
        )

        validation = (
            validate_candidate_profile_extraction(
                extraction_result=(
                    extraction_result
                ),
                prepared_input=(
                    prepared_input
                ),
            )
        )

        if not validation.is_valid:
            raise (
                CandidateProfileValidationFailedError(
                    validation
                )
            )

        validation_issues = (
            _serialize_validation_issues(
                validation
            )
        )

        saved_profile = (
            upsert_candidate_profile(
                user_id=user_id,
                user_cv_id=cv_id,
                schema_version=(
                    CANDIDATE_PROFILE_SCHEMA_VERSION
                ),
                profile_data=(
                    extraction_result
                    .extraction
                    .profile
                    .model_dump(
                        mode="json"
                    )
                ),
                provider="openai",
                model_name=(
                    extraction_result.model_name
                ),
                prompt_version=(
                    extraction_result.prompt_version
                ),
                input_hash=(
                    extraction_result.input_sha256
                ),
                input_token_count=(
                    extraction_result.input_tokens
                ),
                output_token_count=(
                    extraction_result.output_tokens
                ),
                total_token_count=(
                    extraction_result.total_tokens
                ),
                validation_errors=(
                    validation_issues
                ),
                extraction_confidence=(
                    extraction_result
                    .extraction
                    .overall_confidence
                ),
            )
        )

        update_user_cv_processing_status(
            user_id=user_id,
            cv_id=cv_id,
            status="ready",
            processing_error=None,
        )

        outcome: (
            CandidateProfileProcessingOutcome
        ) = (
            "updated"
            if existing_profile is not None
            else "created"
        )

        return (
            CandidateProfileProcessingResult(
                outcome=outcome,
                user_cv_id=cv_id,
                candidate_profile=(
                    saved_profile
                ),
                requires_review=(
                    validation.requires_review
                ),
                validation_issues=tuple(
                    validation_issues
                ),
            )
        )

    except Exception as error:
        safe_error = (
            _safe_processing_error(
                error
            )
        )

        try:
            update_user_cv_processing_status(
                user_id=user_id,
                cv_id=cv_id,
                status="failed",
                processing_error=safe_error,
            )

        except Exception:
            # Een fout bij het registreren van de
            # failure mag de oorspronkelijke fout
            # niet overschrijven.
            pass

        raise