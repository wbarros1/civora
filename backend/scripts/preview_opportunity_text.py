"""Bekijk de voorbewerkte tekst van één ruwe opdracht."""

import argparse
from pathlib import Path
from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)
from backend.app.services.opportunity_text import (
    prepare_opportunity_text,
)


OUTPUT_PATH = Path(
    "tmp/opportunity-text-preview.txt"
)


def parse_arguments() -> argparse.Namespace:
    """Lees optioneel een Flextender-referentienummer."""

    parser = argparse.ArgumentParser(
        description=(
            "Maak een tekstpreview van één "
            "Flextender-opdracht."
        )
    )

    parser.add_argument(
        "--reference",
        type=str,
        default=None,
        help=(
            "Optioneel Flextender-referentienummer. "
            "Zonder waarde wordt een recent actief "
            "record geselecteerd."
        ),
    )

    parser.add_argument(
        "--max-characters",
        type=int,
        default=60_000,
        help=(
            "Maximumlengte van de voorbereide tekst."
        ),
    )

    return parser.parse_args()


def get_raw_opportunity(
    *,
    source_reference: str | None,
) -> dict[str, Any]:
    """Haal één ruwe Flextender-opdracht op."""

    client = get_supabase_client()

    source_response = (
        client.table("sources")
        .select("id")
        .eq("code", "flextender")
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

    query = (
        client.table("raw_opportunities")
        .select(
            "id,"
            "source_reference,"
            "title_hint,"
            "source_status,"
            "processing_status,"
            "normalized_content_hash,"
            "raw_content,"
            "updated_at"
        )
        .eq(
            "source_id",
            source_id,
        )
        .eq(
            "source_status",
            "active",
        )
    )

    if source_reference:
        query = query.eq(
            "source_reference",
            source_reference,
        )

    response = (
        query.order(
            "updated_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Geen passende actieve "
            "Flextender-opdracht gevonden."
        )

    row = rows[0]

    if not isinstance(row, dict):
        raise RuntimeError(
            "Supabase retourneerde een "
            "ongeldig record."
        )

    return row


def main() -> None:
    """Maak en bewaar de tekstpreview."""

    arguments = parse_arguments()

    raw_opportunity = get_raw_opportunity(
        source_reference=(
            arguments.reference
        )
    )

    raw_content = raw_opportunity.get(
        "raw_content"
    )

    if not isinstance(
        raw_content,
        str,
    ):
        raise RuntimeError(
            "De geselecteerde opdracht bevat "
            "geen geldige raw_content."
        )

    prepared = prepare_opportunity_text(
        raw_content,
        max_characters=(
            arguments.max_characters
        ),
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        prepared.text,
        encoding="utf-8",
    )

    print()
    print("Opportunity text preview")
    print("------------------------")
    print(
        "Referentie:       "
        f"{raw_opportunity.get('source_reference')}"
    )
    print(
        "Titelhint:        "
        f"{raw_opportunity.get('title_hint')}"
    )
    print(
        "Status:           "
        f"{raw_opportunity.get('source_status')}"
    )
    print(
        "Originele lengte: "
        f"{prepared.original_character_count}"
    )
    print(
        "Tekstlengte:      "
        f"{prepared.prepared_character_count}"
    )
    print(
        f"Afgekapt:         {prepared.truncated}"
    )
    print(
        f"Bestand:          {OUTPUT_PATH}"
    )
    print()
    print("Eerste 2.000 tekens")
    print("-------------------")
    print(
        prepared.text[:2000]
    )


if __name__ == "__main__":
    main()