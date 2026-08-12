"""Databaseopslag voor gestructureerde opdrachtextracties."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)
from backend.app.services.opportunity_extractor import (
    OpportunityExtractionResult,
)
from backend.app.services.opportunity_postprocessing import (
    PostProcessedExtraction,
)
from backend.app.services.opportunity_text import (
    PreparedOpportunityText,
)


COMPLETED_EXTRACTION_STATUSES = {
    "succeeded",
    "review_required",
}


@dataclass(
    frozen=True,
    slots=True,
)
class ExtractionRunReservation:
    """Gereserveerde of reeds bestaande extractierun."""

    run_id: str
    idempotency_key: str
    should_execute: bool
    existing_status: str | None
    structured_opportunity_id: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class ExtractionPersistenceResult:
    """Resultaat van succesvolle databaseopslag."""

    extraction_run_id: str
    structured_opportunity_id: str
    extraction_status: str
    processing_status: str


def _utc_now_iso() -> str:
    """Geef de actuele UTC-tijd als ISO 8601-string."""

    return datetime.now(
        UTC
    ).isoformat()


def _first_row(
    data: Any,
) -> dict[str, Any] | None:
    """Lees veilig de eerste Supabase-resultaatrij."""

    if not isinstance(
        data,
        list,
    ):
        return None

    if not data:
        return None

    first_row = data[0]

    if not isinstance(
        first_row,
        dict,
    ):
        return None

    return first_row

def build_extraction_idempotency_key(
    *,
    raw_opportunity_id: str,
    input_hash: str,
    prompt_version: str,
    requested_model: str,
    postprocessing_version: str,
) -> str:
    """
    Maak een stabiele sleutel voor één
    inhoud/model/prompt/postprocessing-combinatie.

    Een nieuwe inhoudshash, promptversie, modelnaam
    of postprocessingversie levert bewust een nieuwe
    sleutel op.
    """

    components = (
        raw_opportunity_id.strip(),
        input_hash.strip(),
        prompt_version.strip(),
        requested_model.strip(),
        postprocessing_version.strip(),
    )

    if any(
        not component
        for component in components
    ):
        raise ValueError(
            "Alle onderdelen van de idempotency key "
            "moeten gevuld zijn."
        )

    key_material = "|".join(
        components
    )

    return sha256(
        key_material.encode(
            "utf-8"
        )
    ).hexdigest()

def reserve_extraction_run(
    *,
    raw_opportunity_id: str,
    source_id: str,
    source_reference: str,
    input_hash: str,
    input_character_count: int,
    prompt_version: str,
    requested_model: str,
    postprocessing_version: str,
    request_metadata: dict[str, Any],
) -> ExtractionRunReservation:
    """
    Reserveer een extractierun.

    Een eerder voltooide run met dezelfde idempotency key wordt
    hergebruikt. Een mislukte of onafgemaakte run wordt opnieuw
    op status running gezet.
    """

    client = get_supabase_client()

    idempotency_key = (
        build_extraction_idempotency_key(
            raw_opportunity_id=(
                raw_opportunity_id
            ),
            input_hash=input_hash,
            prompt_version=(
                prompt_version
            ),
            requested_model=(
                requested_model
            ),
            postprocessing_version=(
                postprocessing_version
            ),
        )
    )

    existing_response = (
        client.table(
            "opportunity_extraction_runs"
        )
        .select(
            "id,"
            "status,"
            "structured_opportunity_id"
        )
        .eq(
            "idempotency_key",
            idempotency_key,
        )
        .limit(1)
        .execute()
    )

    existing_row = _first_row(
        existing_response.data
    )

    if existing_row is not None:
        existing_status = str(
            existing_row.get(
                "status",
                "",
            )
        )

        existing_run_id = str(
            existing_row["id"]
        )

        structured_opportunity_id = (
            existing_row.get(
                "structured_opportunity_id"
            )
        )

        if (
            existing_status
            in COMPLETED_EXTRACTION_STATUSES
            and isinstance(
                structured_opportunity_id,
                str,
            )
            and structured_opportunity_id
        ):
            return ExtractionRunReservation(
                run_id=existing_run_id,
                idempotency_key=(
                    idempotency_key
                ),
                should_execute=False,
                existing_status=(
                    existing_status
                ),
                structured_opportunity_id=(
                    structured_opportunity_id
                ),
            )

        restart_payload = {
            "status": "running",
            "provider": "openai",
            "model_name": (
                requested_model
            ),
            "prompt_version": (
                prompt_version
            ),
            "postprocessing_version": (
                postprocessing_version
            ),
            "input_hash": input_hash,
            "input_character_count": (
                input_character_count
            ),
            "request_metadata": (
                request_metadata
            ),
            "raw_response": None,
            "parsed_output": None,
            "validation_errors": [],
            "review_reasons": [],
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "estimated_cost_usd": None,
            "error_type": None,
            "error_message": None,
            "started_at": (
                _utc_now_iso()
            ),
            "completed_at": None,
        }

        (
            client.table(
                "opportunity_extraction_runs"
            )
            .update(
                restart_payload
            )
            .eq(
                "id",
                existing_run_id,
            )
            .execute()
        )

        return ExtractionRunReservation(
            run_id=existing_run_id,
            idempotency_key=(
                idempotency_key
            ),
            should_execute=True,
            existing_status=(
                existing_status
            ),
            structured_opportunity_id=(
                structured_opportunity_id
                if isinstance(
                    structured_opportunity_id,
                    str,
                )
                else None
            ),
        )

    insert_payload = {
        "raw_opportunity_id": (
            raw_opportunity_id
        ),
        "raw_opportunity_version_id": None,
        "structured_opportunity_id": None,
        "source_id": source_id,
        "source_reference": (
            source_reference
        ),
        "status": "running",
        "provider": "openai",
        "model_name": requested_model,
        "prompt_version": prompt_version,
        "postprocessing_version": (
            postprocessing_version
        ),
        "input_hash": input_hash,
        "input_character_count": (
            input_character_count
        ),
        "request_metadata": (
            request_metadata
        ),
        "validation_errors": [],
        "review_reasons": [],
        "idempotency_key": (
            idempotency_key
        ),
        "started_at": (
            _utc_now_iso()
        ),
    }

    insert_response = (
        client.table(
            "opportunity_extraction_runs"
        )
        .insert(
            insert_payload
        )
        .execute()
    )

    inserted_row = _first_row(
        insert_response.data
    )

    if inserted_row is None:
        raise RuntimeError(
            "De extractierun kon niet worden aangemaakt."
        )

    return ExtractionRunReservation(
        run_id=str(
            inserted_row["id"]
        ),
        idempotency_key=(
            idempotency_key
        ),
        should_execute=True,
        existing_status=None,
        structured_opportunity_id=None,
    )


def _build_structured_payload(
    *,
    raw_opportunity: dict[str, Any],
    input_hash: str,
    extraction_result: (
        OpportunityExtractionResult
    ),
    post_processed: (
        PostProcessedExtraction
    ),
) -> dict[str, Any]:
    """Vertaal het gevalideerde model naar databasekolommen."""

    opportunity = (
        post_processed
        .extraction
        .opportunity
    )

    source_status = str(
        raw_opportunity.get(
            "source_status",
            "unknown",
        )
    )

    if source_status not in {
        "active",
        "closed",
        "unknown",
    }:
        source_status = "unknown"

    now_iso = _utc_now_iso()

    return {
        "raw_opportunity_id": (
            raw_opportunity["id"]
        ),
        "source_id": (
            raw_opportunity["source_id"]
        ),
        "source_reference": (
            raw_opportunity[
                "source_reference"
            ]
        ),
        "title": opportunity.title,
        "client_name": (
            opportunity.client_name
        ),
        "description": (
            opportunity.description
        ),
        "location": opportunity.location,
        "province": opportunity.province,
        "work_arrangement": (
            opportunity.work_arrangement
        ),
        "start_date": (
            opportunity.start_date.isoformat()
            if opportunity.start_date
            else None
        ),
        "end_date": (
            opportunity.end_date.isoformat()
            if opportunity.end_date
            else None
        ),
        "application_deadline": (
            opportunity
            .application_deadline
            .isoformat()
            if (
                opportunity
                .application_deadline
            )
            else None
        ),
        "publication_date": (
            opportunity
            .publication_date
            .isoformat()
            if opportunity.publication_date
            else None
        ),
        "hours_per_week_min": (
            opportunity
            .hours_per_week_min
        ),
        "hours_per_week_max": (
            opportunity
            .hours_per_week_max
        ),
        "duration_months": (
            opportunity.duration_months
        ),
        "extension_possible": (
            opportunity
            .extension_possible
        ),
        "number_of_positions": (
            opportunity
            .number_of_positions
        ),
        "rate_min": opportunity.rate_min,
        "rate_max": opportunity.rate_max,
        "rate_currency": (
            opportunity.rate_currency
        ),
        "rate_period": (
            opportunity.rate_period
        ),
        "employment_relationship": (
            opportunity
            .employment_relationship
        ),
        "education_level": (
            opportunity.education_level
        ),
        "minimum_years_experience": (
            opportunity
            .minimum_years_experience
        ),
        "requirements": (
            opportunity.requirements
        ),
        "wishes": opportunity.wishes,
        "competencies": (
            opportunity.competencies
        ),
        "skills": opportunity.skills,
        "contact_information": (
            opportunity
            .contact_information
            .model_dump(
                mode="json"
            )
        ),
        "source_status": source_status,
        "application_status": (
            post_processed
            .application_status
        ),
        "extraction_confidence": (
            post_processed
            .extraction
            .overall_confidence
        ),
        "review_required": (
            post_processed
            .review_required
        ),
        "review_reasons": (
            post_processed
            .extraction
            .review_reasons
        ),
        "extracted_from_hash": (
            input_hash
        ),
        "extraction_prompt_version": (
            extraction_result
            .prompt_version
        ),
        "extraction_model": (
            extraction_result
            .model_name
        ),
        "extracted_at": now_iso,
        "updated_at": now_iso,
    }


def persist_successful_extraction(
    *,
    reservation: ExtractionRunReservation,
    raw_opportunity: dict[str, Any],
    input_hash: str,
    requested_model: str,
    prepared: PreparedOpportunityText,
    extraction_result: (
        OpportunityExtractionResult
    ),
    post_processed: (
        PostProcessedExtraction
    ),
) -> ExtractionPersistenceResult:
    """Sla de huidige opdracht en de volledige extractierun op."""

    client = get_supabase_client()

    structured_payload = (
        _build_structured_payload(
            raw_opportunity=(
                raw_opportunity
            ),
            input_hash=input_hash,
            extraction_result=(
                extraction_result
            ),
            post_processed=(
                post_processed
            ),
        )
    )

    (
        client.table(
            "structured_opportunities"
        )
        .upsert(
            structured_payload,
            on_conflict=(
                "raw_opportunity_id"
            ),
        )
        .execute()
    )

    structured_response = (
        client.table(
            "structured_opportunities"
        )
        .select("id")
        .eq(
            "raw_opportunity_id",
            raw_opportunity["id"],
        )
        .limit(1)
        .execute()
    )

    structured_row = _first_row(
        structured_response.data
    )

    if structured_row is None:
        raise RuntimeError(
            "De gestructureerde opdracht kon "
            "na de upsert niet worden teruggevonden."
        )

    structured_opportunity_id = str(
        structured_row["id"]
    )

    extraction_status = (
        "review_required"
        if post_processed.review_required
        else "succeeded"
    )

    processing_status = (
        "review_required"
        if post_processed.review_required
        else "processed"
    )

    completed_at = _utc_now_iso()

    run_metadata = {
        "response_id": (
            extraction_result.response_id
        ),
        "requested_model": (
            requested_model
        ),
        "resolved_model": (
            extraction_result.model_name
        ),
        "application_status": (
            post_processed
            .application_status
        ),
        "corrections": list(
            post_processed.corrections
        ),
        "source_status": (
            raw_opportunity.get(
                "source_status"
            )
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
    }

    run_payload = {
        "structured_opportunity_id": (
            structured_opportunity_id
        ),
        "status": extraction_status,
        "provider": "openai",
        "model_name": (
            requested_model
        ),
        "prompt_version": (
            extraction_result
            .prompt_version
        ),
        "overall_confidence": (
            post_processed
            .extraction
            .overall_confidence
        ),
        "request_metadata": (
            run_metadata
        ),
        "raw_response": None,
        "parsed_output": (
            post_processed
            .extraction
            .model_dump(
                mode="json"
            )
        ),
        "validation_errors": [],
        "review_reasons": (
            post_processed
            .extraction
            .review_reasons
        ),
        "input_tokens": (
            extraction_result
            .input_tokens
        ),
        "output_tokens": (
            extraction_result
            .output_tokens
        ),
        "total_tokens": (
            extraction_result
            .total_tokens
        ),
        "error_type": None,
        "error_message": None,
        "completed_at": completed_at,
    }

    (
        client.table(
            "opportunity_extraction_runs"
        )
        .update(
            run_payload
        )
        .eq(
            "id",
            reservation.run_id,
        )
        .execute()
    )

    (
        client.table(
            "raw_opportunities"
        )
        .update(
            {
                "processing_status": (
                    processing_status
                ),
                "updated_at": (
                    completed_at
                ),
            }
        )
        .eq(
            "id",
            raw_opportunity["id"],
        )
        .execute()
    )

    return ExtractionPersistenceResult(
        extraction_run_id=(
            reservation.run_id
        ),
        structured_opportunity_id=(
            structured_opportunity_id
        ),
        extraction_status=(
            extraction_status
        ),
        processing_status=(
            processing_status
        ),
    )


def mark_extraction_failed(
    *,
    reservation: ExtractionRunReservation,
    raw_opportunity_id: str,
    error: Exception,
) -> None:
    """Markeer een gereserveerde extractierun als mislukt."""

    client = get_supabase_client()

    completed_at = _utc_now_iso()

    (
        client.table(
            "opportunity_extraction_runs"
        )
        .update(
            {
                "status": "failed",
                "error_type": (
                    type(error).__name__
                ),
                "error_message": str(
                    error
                )[:4000],
                "completed_at": (
                    completed_at
                ),
            }
        )
        .eq(
            "id",
            reservation.run_id,
        )
        .execute()
    )

    (
        client.table(
            "raw_opportunities"
        )
        .update(
            {
                "processing_status": (
                    "failed"
                ),
                "updated_at": (
                    completed_at
                ),
            }
        )
        .eq(
            "id",
            raw_opportunity_id,
        )
        .execute()
    )