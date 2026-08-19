"""Classificeer een batch actieve Civora-opportunities."""

import argparse
import json
from pathlib import Path

from backend.app.repositories.opportunity_classifications import (
    list_opportunities_for_classification,
)
from backend.app.services.opportunity_classification_pipeline import (
    execute_opportunity_classification,
)
from backend.app.services.opportunity_classifier import (
    CLASSIFIER_VERSION,
)


DEFAULT_LIMIT = 10

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
    """Lees batchinstellingen."""

    parser = argparse.ArgumentParser(
        description=(
            "Classificeer een batch actieve "
            "Civora-opportunities."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            "Maximum aantal opdrachten "
            "in deze batch."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Toon welke opdrachten geselecteerd "
            "worden zonder OpenAI aan te roepen."
        ),
    )

    return parser.parse_args()


def save_output_payload(
    *,
    source_reference: str,
    output_payload: dict,
) -> Path:
    """Bewaar classifier-output lokaal."""

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / f"{source_reference}.json"
    )

    output_path.write_text(
        json.dumps(
            output_payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    """Verwerk één sequentiële classificatiebatch."""

    arguments = parse_arguments()

    if arguments.limit < 1:
        raise ValueError(
            "--limit moet minimaal 1 zijn."
        )

    references = (
        list_opportunities_for_classification(
            classifier_version=(
                CLASSIFIER_VERSION
            ),
            limit=arguments.limit,
        )
    )

    print()
    print("Civora batchclassificatie")
    print("-------------------------")
    print(
        "Classifier:    "
        f"{CLASSIFIER_VERSION}"
    )
    print(
        f"Limit:         {arguments.limit}"
    )
    print(
        f"Geselecteerd:  {len(references)}"
    )

    if not references:
        print()
        print(
            "Geen actieve opdrachten "
            "meer te classificeren."
        )
        return

    print(
        "Referenties:   "
        + ", ".join(
            references
        )
    )

    if arguments.dry_run:
        print()
        print(
            "Dry-run voltooid. "
            "Er zijn geen classificaties uitgevoerd."
        )
        return

    classified = 0
    skipped = 0
    failed = 0

    total_input_tokens = 0
    total_output_tokens = 0

    failures: list[
        tuple[str, str]
    ] = []

    print()
    print("Batch gestart")
    print("-------------")

    for index, reference in enumerate(
        references,
        start=1,
    ):
        print()
        print(
            f"[{index}/{len(references)}] "
            f"Referentie {reference}"
        )

        try:
            result = (
                execute_opportunity_classification(
                    reference
                )
            )

            if (
                result.outcome
                == "skipped"
            ):
                skipped += 1

                print(
                    "  Status:  skipped"
                )
                print(
                    "  Reden:   reeds verwerkt "
                    "met deze classifier-versie"
                )

                continue

            output_payload = (
                result.output_payload
            )

            if output_payload is None:
                raise RuntimeError(
                    "Succesvolle classificatie "
                    "bevat geen output_payload."
                )

            output_path = (
                save_output_payload(
                    source_reference=reference,
                    output_payload=(
                        output_payload
                    ),
                )
            )

            usage = (
                output_payload.get(
                    "usage",
                    {},
                )
            )

            total_input_tokens += int(
                usage.get(
                    "input_tokens"
                )
                or 0
            )

            total_output_tokens += int(
                usage.get(
                    "output_tokens"
                )
                or 0
            )

            decision = (
                output_payload[
                    "decision"
                ]
            )

            primary = (
                decision[
                    "primary_vakgroep"
                ]
            )

            matches = (
                decision[
                    "matches"
                ]
            )

            classified += 1

            print(
                "  Status:     classified"
            )

            print(
                "  Primair:    "
                f"{VAKGROEP_LABELS[primary]}"
            )

            if matches:
                match_text = ", ".join(
                    (
                        f"{VAKGROEP_LABELS[match['vakgroep']]}"
                        f" ({match['relevance_score']})"
                    )
                    for match in matches
                )
            else:
                match_text = "Geen"

            print(
                "  Matches:    "
                f"{match_text}"
            )

            print(
                "  Confidence: "
                f"{decision['classification_confidence']}"
            )

            print(
                "  Bestand:    "
                f"{output_path}"
            )

        except Exception as error:
            failed += 1

            failures.append(
                (
                    reference,
                    str(error),
                )
            )

            print(
                "  Status: failed"
            )

            print(
                "  Fout:   "
                f"{error}"
            )

            continue

    print()
    print("Batch voltooid")
    print("---------------")

    print(
        f"Geselecteerd:    {len(references)}"
    )

    print(
        f"Geclassificeerd: {classified}"
    )

    print(
        f"Overgeslagen:    {skipped}"
    )

    print(
        f"Mislukt:         {failed}"
    )

    print(
        "Inputtokens:      "
        f"{total_input_tokens}"
    )

    print(
        "Outputtokens:     "
        f"{total_output_tokens}"
    )

    if failures:
        print()
        print("Mislukte opdrachten")
        print("-------------------")

        for reference, message in failures:
            print(
                f"- {reference}: {message}"
            )


if __name__ == "__main__":
    main()