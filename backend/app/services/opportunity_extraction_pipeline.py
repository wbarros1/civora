"""Gedeelde pipeline voor opportunity-extractie."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from backend.app.core.config import (
    get_settings,
)
from backend.app.database.client import (
    get_supabase_client,
)
from backend.app.repositories.opportunity_extractions import (
    mark_extraction_failed,
    persist_successful_extraction,
    reserve_extraction_run,
)
from backend.app.services.opportunity_extractor import (
    PROMPT_VERSION,
    extract_opportunity_with_llm,
)
from backend.app.services.opportunity_postprocessing import (
    POSTPROCESSING_VERSION,
    post_process_extraction,
)
from backend.app.services.opportunity_text import (
    prepare_opportunity_text,
)

from backend.app.services.opportunity_classification_pipeline import (
    execute_opportunity_classification,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ExtractionExecutionResult:
    """Resultaat van één extractiepoging."""

    source_reference: str
    outcome: str
    extraction_run_id: str
    existing_status: str | None
    structured_opportunity_id: str | None
    output_payload: dict[str, Any] | None

    classification_outcome: str | None = None
    classification_id: str | None = None
    classification_error: str | None = None


def get_raw_opportunity(
    source_reference: str,
) -> dict[str, Any]:
    """Haal één ruwe Flextender-opdracht op."""

    client = get_supabase_client()

    source_response = (
        client.table("sources")
        .select("id")
        .eq(
            "code",
            "flextender",
        )
        .limit(1)
        .execute()
    )

    source_rows = (
        source_response.data or []
    )

    if not source_rows:
        raise RuntimeError(
            "Bron flextender is niet gevonden."
        )

    source_id = source_rows[0]["id"]

    response = (
        client.table("raw_opportunities")
        .select(
            "id,"
            "source_id,"
            "source_reference,"
            "title_hint,"
            "source_status,"
            "normalized_content_hash,"
            "raw_content,"
            "updated_at"
        )
        .eq(
            "source_id",
            source_id,
        )
        .eq(
            "source_reference",
            source_reference,
        )
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Geen Flextender-opdracht gevonden "
            f"voor referentie {source_reference}."
        )

    row = rows[0]

    if not isinstance(
        row,
        dict,
    ):
        raise RuntimeError(
            "Supabase retourneerde een "
            "ongeldig record."
        )

    return row


def determine_input_hash(
    *,
    raw_opportunity: dict[str, Any],
    prepared_text: str,
) -> str:
    """Gebruik de bronhash of bereken een teksthash."""

    normalized_content_hash = (
        raw_opportunity.get(
            "normalized_content_hash"
        )
    )

    if (
        isinstance(
            normalized_content_hash,
            str,
        )
        and normalized_content_hash.strip()
    ):
        return (
            normalized_content_hash
            .strip()
        )

    return sha256(
        prepared_text.encode(
            "utf-8"
        )
    ).hexdigest()

@dataclass(
    frozen=True,
    slots=True,
)
class PostExtractionClassificationResult:
    """Resultaat van automatische classificatie na extraction."""

    outcome: str
    classification_id: str | None
    error: str | None


def execute_post_extraction_classification(
    source_reference: str,
) -> PostExtractionClassificationResult:
    """
    Classificeer een geëxtraheerde opportunity.

    Een classificatiefout mag de reeds geslaagde extraction
    nooit terugdraaien of als failed markeren.
    """

    try:
        result = (
            execute_opportunity_classification(
                source_reference
            )
        )

        return PostExtractionClassificationResult(
            outcome=result.outcome,
            classification_id=(
                result.classification_id
            ),
            error=None,
        )

    except Exception as error:
        return PostExtractionClassificationResult(
            outcome="failed",
            classification_id=None,
            error=(
                f"{type(error).__name__}: "
                f"{str(error)[:4000]}"
            ),
        )

def execute_opportunity_extraction(
    source_reference: str,
) -> ExtractionExecutionResult:
    """Voer één volledige extractiepipeline uit."""

    raw_opportunity = get_raw_opportunity(
        source_reference
    )

    raw_content = raw_opportunity.get(
        "raw_content"
    )

    if not isinstance(
        raw_content,
        str,
    ):
        raise RuntimeError(
            "De opdracht bevat geen "
            "geldige raw_content."
        )

    prepared = prepare_opportunity_text(
        raw_content
    )

    input_hash = determine_input_hash(
        raw_opportunity=raw_opportunity,
        prepared_text=prepared.text,
    )

    settings = get_settings()

    requested_model = (
        settings.openai_extraction_model
    )

    reservation = reserve_extraction_run(
        raw_opportunity_id=(
            raw_opportunity["id"]
        ),
        source_id=(
            raw_opportunity["source_id"]
        ),
        source_reference=(
            raw_opportunity[
                "source_reference"
            ]
        ),
        input_hash=input_hash,
        input_character_count=(
            prepared
            .prepared_character_count
        ),
        prompt_version=(
            PROMPT_VERSION
        ),
        requested_model=(
            requested_model
        ),
        postprocessing_version=(
            POSTPROCESSING_VERSION
        ),
        request_metadata={
            "requested_model": (
                requested_model
            ),
            "prepared_text": {
                "original_character_count": (
                    prepared
                    .original_character_count
                ),
                "prepared_character_count": (
                    prepared
                    .prepared_character_count
                ),
                "truncated": (
                    prepared.truncated
                ),
            },
        },
    )

    if not reservation.should_execute:
        classification_result = None

        if (
            reservation
            .structured_opportunity_id
            is not None
        ):
            classification_result = (
                execute_post_extraction_classification(
                    str(
                        raw_opportunity[
                            "source_reference"
                        ]
                    )
                )
            )

        return ExtractionExecutionResult(
            source_reference=str(
                raw_opportunity[
                    "source_reference"
                ]
            ),
            outcome="skipped",
            extraction_run_id=str(
                reservation.run_id
            ),
            existing_status=(
                reservation.existing_status
            ),
            structured_opportunity_id=(
                str(
                    reservation
                    .structured_opportunity_id
                )
                if (
                    reservation
                    .structured_opportunity_id
                    is not None
                )
                else None
            ),
            output_payload=None,
            classification_outcome=(
                classification_result.outcome
                if classification_result
                is not None
                else None
            ),
            classification_id=(
                classification_result
                .classification_id
                if classification_result
                is not None
                else None
            ),
            classification_error=(
                classification_result.error
                if classification_result
                is not None
                else None
            ),
        )

    try:
        extraction_result = (
            extract_opportunity_with_llm(
                prepared.text
            )
        )

        raw_source_status = str(
            raw_opportunity.get(
                "source_status",
                "unknown",
            )
        )

        post_processed = (
            post_process_extraction(
                extraction=(
                    extraction_result
                    .extraction
                ),
                prepared_text=(
                    prepared.text
                ),
                title_hint=(
                    raw_opportunity.get(
                        "title_hint"
                    )
                ),
                source_status=(
                    raw_source_status
                ),
            )
        )

        persistence = (
            persist_successful_extraction(
                reservation=reservation,
                raw_opportunity=(
                    raw_opportunity
                ),
                input_hash=input_hash,
                requested_model=(
                    requested_model
                ),
                prepared=prepared,
                extraction_result=(
                    extraction_result
                ),
                post_processed=(
                    post_processed
                ),
            )
        )

    except Exception as error:
        mark_extraction_failed(
            reservation=reservation,
            raw_opportunity_id=(
                raw_opportunity["id"]
            ),
            error=error,
        )

        raise

    classification_result = (
        execute_post_extraction_classification(
            str(
                raw_opportunity[
                    "source_reference"
                ]
            )
        )
    )

    output_payload = {
        "source_reference": (
            raw_opportunity[
                "source_reference"
            ]
        ),
        "raw_opportunity_id": (
            raw_opportunity["id"]
        ),
        "raw_source_status": (
            raw_source_status
        ),
        "application_status": (
            post_processed
            .application_status
        ),
        "normalized_content_hash": (
            raw_opportunity.get(
                "normalized_content_hash"
            )
        ),
        "response_id": (
            extraction_result.response_id
        ),
        "model_name": (
            extraction_result.model_name
        ),
        "prompt_version": (
            extraction_result.prompt_version
        ),
        "postprocessing_version": (
            POSTPROCESSING_VERSION
        ),
        "usage": {
            "input_tokens": (
                extraction_result.input_tokens
            ),
            "output_tokens": (
                extraction_result.output_tokens
            ),
            "total_tokens": (
                extraction_result.total_tokens
            ),
        },
        "prepared_text": {
            "original_character_count": (
                prepared
                .original_character_count
            ),
            "prepared_character_count": (
                prepared
                .prepared_character_count
            ),
            "truncated": (
                prepared.truncated
            ),
        },
        "review_required": (
            post_processed.review_required
        ),
        "corrections": list(
            post_processed.corrections
        ),
        "extraction": (
            post_processed
            .extraction
            .model_dump(
                mode="json"
            )
        ),
        "classification": {
            "outcome": (
                classification_result
                .outcome
            ),
            "classification_id": (
                classification_result
                .classification_id
            ),
            "error": (
                classification_result
                .error
            ),
        },
        "database": {
            "extraction_run_id": (
                persistence
                .extraction_run_id
            ),
            "structured_opportunity_id": (
                persistence
                .structured_opportunity_id
            ),
            "extraction_status": (
                persistence
                .extraction_status
            ),
            "processing_status": (
                persistence
                .processing_status
            ),
        },
    }

    return ExtractionExecutionResult(
        source_reference=str(
            raw_opportunity[
                "source_reference"
            ]
        ),
        outcome="succeeded",
        extraction_run_id=str(
            persistence.extraction_run_id
        ),
        existing_status=None,
        structured_opportunity_id=str(
            persistence
            .structured_opportunity_id
        ),
        output_payload=output_payload,
        classification_outcome=(
            classification_result
            .outcome
        ),
        classification_id=(
            classification_result
            .classification_id
        ),
        classification_error=(
            classification_result
            .error
        ),
    )