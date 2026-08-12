"""Voer één gecontroleerde LLM-extractie uit."""

import argparse
import json
from pathlib import Path

from backend.app.services.opportunity_extraction_pipeline import (
    execute_opportunity_extraction,
)


OUTPUT_DIRECTORY = Path(
    "tmp/opportunity-extractions"
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


def main() -> None:
    """Extraheer één opdracht."""

    arguments = parse_arguments()

    result = execute_opportunity_extraction(
        arguments.reference
    )

    print()

    if result.outcome == "skipped":
        print("Extractie overgeslagen")
        print("----------------------")
        print(
            "Referentie:       "
            f"{result.source_reference}"
        )
        print(
            "Bestaande status: "
            f"{result.existing_status}"
        )
        print(
            "Extractierun:     "
            f"{result.extraction_run_id}"
        )
        print(
            "Structured ID:    "
            f"{result.structured_opportunity_id}"
        )
        print(
            "Reden:            dezelfde content, "
            "promptversie, model- en "
            "postprocessingcombinatie is al verwerkt."
        )

        return

    output_payload = (
        result.output_payload
    )

    if output_payload is None:
        raise RuntimeError(
            "Succesvolle extractie bevat "
            "geen output_payload."
        )

    opportunity = (
        output_payload["extraction"][
            "opportunity"
        ]
    )

    database = (
        output_payload["database"]
    )

    usage = (
        output_payload["usage"]
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / f"{result.source_reference}.json"
    )

    output_path.write_text(
        json.dumps(
            output_payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("LLM-extractie voltooid")
    print("-----------------------")

    print(
        "Referentie:     "
        f"{result.source_reference}"
    )

    print(
        "Titel:          "
        f"{opportunity.get('title')}"
    )

    print(
        "Opdrachtgever:  "
        f"{opportunity.get('client_name')}"
    )

    print(
        "Startdatum:     "
        f"{opportunity.get('start_date')}"
    )

    print(
        "Einddatum:      "
        f"{opportunity.get('end_date')}"
    )

    print(
        "Deadline:       "
        f"{opportunity.get('application_deadline')}"
    )

    print(
        "Bronstatus:     "
        f"{output_payload['raw_source_status']}"
    )

    print(
        "Reactiestatus:  "
        f"{output_payload['application_status']}"
    )

    print(
        "Uren:           "
        f"{opportunity.get('hours_per_week_min')}"
        " - "
        f"{opportunity.get('hours_per_week_max')}"
    )

    print(
        "Maximumtarief:  "
        f"{opportunity.get('rate_max')} "
        f"{opportunity.get('rate_currency')}"
    )

    print(
        "Confidence:     "
        f"{output_payload['extraction'].get('overall_confidence')}"
    )

    print(
        "Inputtokens:    "
        f"{usage.get('input_tokens')}"
    )

    print(
        "Outputtokens:   "
        f"{usage.get('output_tokens')}"
    )

    print(
        "Review nodig:   "
        f"{output_payload['review_required']}"
    )

    print(
        "Correcties:     "
        f"{len(output_payload['corrections'])}"
    )

    print(
        "Extractiestatus: "
        f"{database['extraction_status']}"
    )

    print(
        "Processingstatus: "
        f"{database['processing_status']}"
    )

    print(
        "Extractierun:    "
        f"{database['extraction_run_id']}"
    )

    print(
        "Structured ID:   "
        f"{database['structured_opportunity_id']}"
    )

    print(
        "Bestand:         "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()