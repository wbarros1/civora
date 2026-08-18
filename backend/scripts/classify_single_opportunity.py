"""Classificeer één Civora-opdracht op vakgroep."""

import argparse
import json
from pathlib import Path

from backend.app.services.opportunity_classification_pipeline import (
    execute_opportunity_classification,
)


OUTPUT_DIRECTORY = Path(
    "tmp/opportunity-classifications"
)


VAKGROEP_LABELS = {
    "procesmanagement":
        "Procesmanagement",
    "data_ai":
        "Data & AI",
    "ict":
        "ICT",
    "finance":
        "Finance",
    "overige":
        "Overige",
}


def parse_arguments() -> argparse.Namespace:
    """Lees het verplichte referentienummer."""

    parser = argparse.ArgumentParser(
        description=(
            "Classificeer één Civora-opdracht "
            "naar vakgroepen."
        )
    )

    parser.add_argument(
        "--reference",
        required=True,
        help=(
            "Het Flextender-"
            "referentienummer."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Classificeer één opdracht."""

    arguments = parse_arguments()

    result = (
        execute_opportunity_classification(
            arguments.reference
        )
    )

    print()

    if result.outcome == "skipped":
        print(
            "Classificatie overgeslagen"
        )
        print(
            "--------------------------"
        )

        print(
            "Referentie:       "
            f"{result.source_reference}"
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
            "Classification:   "
            f"{result.classification_id}"
        )

        print(
            "Reden:            deze "
            "extractierun is al verwerkt "
            "met deze classifier-versie."
        )

        return

    payload = (
        result.output_payload
    )

    if payload is None:
        raise RuntimeError(
            "Succesvolle classificatie bevat "
            "geen output_payload."
        )

    decision = payload[
        "decision"
    ]

    usage = payload[
        "usage"
    ]

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
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "Civora vakgroepclassificatie voltooid"
    )
    print(
        "------------------------------------"
    )

    print(
        "Referentie:       "
        f"{result.source_reference}"
    )

    print(
        "Classifier:       "
        f"{payload['classifier_version']}"
    )

    print()

    print("Scores")
    print("------")

    for score in payload[
        "scores"
    ]:
        label = (
            VAKGROEP_LABELS[
                score["vakgroep"]
            ]
        )

        print(
            f"{label:<18} "
            f"{score['relevance_score']:>3}"
        )

    print()

    primary = (
        decision[
            "primary_vakgroep"
        ]
    )

    print(
        "Primair:          "
        f"{VAKGROEP_LABELS[primary]}"
    )

    matches = (
        decision[
            "matches"
        ]
    )

    if matches:
        match_text = ", ".join(
            VAKGROEP_LABELS[
                match["vakgroep"]
            ]
            for match in matches
        )
    else:
        match_text = "Geen"

    print(
        "Matches:          "
        f"{match_text}"
    )

    print(
        "Confidence:       "
        f"{decision['classification_confidence']}"
    )

    print(
        "Reviewredenen:    "
        f"{len(decision['review_reasons'])}"
    )

    print(
        "Inputtokens:      "
        f"{usage.get('input_tokens')}"
    )

    print(
        "Outputtokens:     "
        f"{usage.get('output_tokens')}"
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
        "Classification:   "
        f"{result.classification_id}"
    )

    print(
        "Bestand:          "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()