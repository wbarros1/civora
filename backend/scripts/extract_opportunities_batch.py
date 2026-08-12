"""Extraheer een batch openstaande opportunities."""

import argparse
import json
from pathlib import Path

from backend.app.repositories.opportunity_extractions import (
    list_opportunities_for_extraction,
)
from backend.app.services.opportunity_extraction_pipeline import (
    execute_opportunity_extraction,
)


DEFAULT_LIMIT = 10

OUTPUT_DIRECTORY = Path(
    "tmp/opportunity-extractions"
)


def parse_arguments() -> argparse.Namespace:
    """Lees batchinstellingen."""

    parser = argparse.ArgumentParser(
        description=(
            "Extraheer een batch actieve "
            "Flextender-opdrachten."
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
            "worden zonder extracties uit te voeren."
        ),
    )

    return parser.parse_args()


def save_output_payload(
    *,
    source_reference: str,
    output_payload: dict,
) -> Path:
    """Bewaar succesvolle output lokaal voor debugging."""

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
    """Verwerk één sequentiële batch."""

    arguments = parse_arguments()

    if arguments.limit < 1:
        raise ValueError(
            "--limit moet minimaal 1 zijn."
        )

    references = (
        list_opportunities_for_extraction(
            source_code="flextender",
            limit=arguments.limit,
        )
    )

    print()
    print("Batchselectie")
    print("-------------")
    print(
        f"Limit:        {arguments.limit}"
    )
    print(
        f"Geselecteerd: {len(references)}"
    )

    if not references:
        print()
        print(
            "Geen pending opdrachten gevonden."
        )
        return

    print(
        "Referenties:  "
        + ", ".join(
            references
        )
    )

    if arguments.dry_run:
        print()
        print(
            "Dry-run voltooid. "
            "Er zijn geen extracties uitgevoerd."
        )
        return

    succeeded = 0
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
                execute_opportunity_extraction(
                    reference
                )
            )

            if result.outcome == "skipped":
                skipped += 1

                print(
                    "  Status: skipped"
                )
                print(
                    "  Bestaande status: "
                    f"{result.existing_status}"
                )

                continue

            output_payload = (
                result.output_payload
            )

            if output_payload is None:
                raise RuntimeError(
                    "Succesvolle extractie bevat "
                    "geen output_payload."
                )

            save_output_payload(
                source_reference=reference,
                output_payload=output_payload,
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

            succeeded += 1

            opportunity = (
                output_payload[
                    "extraction"
                ][
                    "opportunity"
                ]
            )

            print(
                "  Status: succeeded"
            )
            print(
                "  Titel:  "
                f"{opportunity.get('title')}"
            )
            print(
                "  Klant:  "
                f"{opportunity.get('client_name')}"
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
        f"Geselecteerd: {len(references)}"
    )
    print(
        f"Succeeded:    {succeeded}"
    )
    print(
        f"Skipped:      {skipped}"
    )
    print(
        f"Failed:       {failed}"
    )
    print(
        "Inputtokens:   "
        f"{total_input_tokens}"
    )
    print(
        "Outputtokens:  "
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