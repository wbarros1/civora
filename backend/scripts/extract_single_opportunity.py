"""Voer één gecontroleerde LLM-extractie uit."""

import argparse
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from backend.app.database.client import (
    get_supabase_client,
)

from backend.app.services.opportunity_text import (
    prepare_opportunity_text,
)

from backend.app.services.opportunity_postprocessing import (
    post_process_extraction,
)

from hashlib import sha256

from backend.app.core.config import (
    get_settings,
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


OUTPUT_DIRECTORY = Path(
    "tmp/opportunity-extractions"
)

AMSTERDAM_TIMEZONE = ZoneInfo(
    "Europe/Amsterdam"
)


def parse_arguments() -> argparse.Namespace:
    """Lees het verplichte referentienummer."""

    parser = argparse.ArgumentParser(
        description=(
            "Extraheer één Flextender-opdracht "
            "met het ingestelde LLM."
        )
    )

    parser.add_argument(
        "--reference",
        required=True,
        help=(
            "Het numerieke Flextender-"
            "referentienummer."
        ),
    )

    return parser.parse_args()


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

    if not isinstance(row, dict):
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
    """Gebruik de stabiele bronhash of bereken een teksthash."""

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

def main() -> None:
    """Extraheer en bewaar een lokale JSON-preview."""

    arguments = parse_arguments()

    raw_opportunity = get_raw_opportunity(
        arguments.reference
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

    print()

    if not reservation.should_execute:
        print()
        print("Extractie overgeslagen")
        print("----------------------")
        print(
            "Referentie:       "
            f"{raw_opportunity['source_reference']}"
        )
        print(
            "Bestaande status: "
            f"{reservation.existing_status}"
        )
        print(
            "Extractierun:     "
            f"{reservation.run_id}"
        )
        print(
            "Structured ID:    "
            f"{reservation.structured_opportunity_id}"
        )
        print(
            "Reden:            "
            "dezelfde content, promptversie en "
            "modelcombinatie is al verwerkt."
        )

        return



    print("LLM-extractie gestart")
    print("----------------------")
    print(
        "Referentie: "
        f"{raw_opportunity['source_reference']}"
    )
    print(
        "Titelhint:  "
        f"{raw_opportunity.get('title_hint')}"
    )
    print(
        "Tekstlengte: "
        f"{prepared.prepared_character_count}"
    )

    try:
        result = extract_opportunity_with_llm(
            prepared.text
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
                    result.extraction
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
                extraction_result=result,
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



    opportunity = (
        post_processed
        .extraction
        .opportunity
    )

    application_status = (
        post_processed.application_status
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
            application_status
        ),
        "normalized_content_hash": (
            raw_opportunity.get(
                "normalized_content_hash"
            )
        ),
        "response_id": (
            result.response_id
        ),
        "model_name": (
            result.model_name
        ),
        "prompt_version": (
            result.prompt_version
        ),
        "usage": {
            "input_tokens": (
                result.input_tokens
            ),
            "output_tokens": (
                result.output_tokens
            ),
            "total_tokens": (
                result.total_tokens
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

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / (
            f"{arguments.reference}.json"
        )
    )

    output_path.write_text(
        json.dumps(
            output_payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("LLM-extractie voltooid")
    print("-----------------------")
    print(
        f"Titel:          {opportunity.title}"
    )
    print(
        "Opdrachtgever:  "
        f"{opportunity.client_name}"
    )
    print(
        "Startdatum:     "
        f"{opportunity.start_date}"
    )
    print(
        "Einddatum:      "
        f"{opportunity.end_date}"
    )
    print(
        "Deadline:       "
        f"{opportunity.application_deadline}"
    )
    print(
        "Bronstatus:     "
        f"{raw_source_status}"
    )
    print(
        "Reactiestatus:  "
        f"{application_status}"
    )
    print(
        "Uren:           "
        f"{opportunity.hours_per_week_min}"
        " - "
        f"{opportunity.hours_per_week_max}"
    )
    print(
        "Maximumtarief:  "
        f"{opportunity.rate_max} "
        f"{opportunity.rate_currency}"
    )
    print(
        "Confidence:     "
        f"{result.extraction.overall_confidence}"
    )
    print(
        "Inputtokens:    "
        f"{result.input_tokens}"
    )
    print(
        "Outputtokens:   "
        f"{result.output_tokens}"
    )
    print(
        "Review nodig:   "
        f"{post_processed.review_required}"
    )

    print(
        "Correcties:     "
        f"{len(post_processed.corrections)}"
    )

    print(
        "Extractiestatus:"
        f" {persistence.extraction_status}"
    )

    print(
        "Processingstatus:"
        f" {persistence.processing_status}"
    )

    print(
        "Extractierun:    "
        f"{persistence.extraction_run_id}"
    )

    print(
        "Structured ID:   "
        f"{persistence.structured_opportunity_id}"
    )
    print(
        f"Bestand:        {output_path}"
    )


if __name__ == "__main__":
    main()