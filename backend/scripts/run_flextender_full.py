"""Voer een volledige Flextender-ingestion uit."""

import argparse

from backend.app.connectors.flextender.connector import (
    run_flextender_connector,
)


def parse_arguments() -> argparse.Namespace:
    """Lees commandoregelargumenten."""

    parser = argparse.ArgumentParser(
        description=(
            "Verwerk alle momenteel ontdekte "
            "Flextender-opdrachten."
        )
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help=(
            "Aantal opdrachten per logische batch. "
            "Standaard: 25."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Start de volledige Flextender-run."""

    arguments = parse_arguments()

    summary = run_flextender_connector(
        process_all=True,
        batch_size=arguments.batch_size,
    )

    print()
    print("Volledige Flextender-run voltooid")
    print("---------------------------------")
    print(
        f"Fetch run:     {summary.fetch_run_id}"
    )
    print(
        f"Gevonden:      {summary.discovered}"
    )
    print(
        f"Geselecteerd:  {summary.selected}"
    )
    print(
        f"Nieuw:         {summary.created}"
    )
    print(
        f"Gewijzigd:     {summary.changed}"
    )
    print(
        f"Ongewijzigd:   {summary.unchanged}"
    )
    print(
        f"Mislukt:       {summary.failed}"
    )
    print(
        "Verdwenen gesloten: "
        f"{summary.closed_missing}"
    )
    print(
        "Closure uitgevoerd: "
        f"{summary.missing_closure_executed}"
    )    

    if summary.errors:
        print()
        print("Meldingen:")

        for error in summary.errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()