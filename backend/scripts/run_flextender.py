"""Start de Flextender-connector handmatig."""

import argparse

from backend.app.connectors.flextender.connector import (
    run_flextender_connector,
)


def parse_arguments() -> argparse.Namespace:
    """Lees commandoregelargumenten."""

    parser = argparse.ArgumentParser(
        description=(
            "Haal openbare Flextender-opdrachten op."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help=(
            "Maximumaantal detailpagina's dat "
            "wordt opgehaald. Standaard: 1."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Voer de connector uit en toon een samenvatting."""

    arguments = parse_arguments()

    try:
        summary = run_flextender_connector(
            max_items=arguments.limit
        )
    except Exception as exc:
        print()
        print("Flextender-connector mislukt")
        print("----------------------------")
        print(str(exc))
        raise SystemExit(1) from exc

    print()
    print("Flextender-connector voltooid")
    print("-----------------------------")
    print(f"Fetch run:     {summary.fetch_run_id}")
    print(f"Gevonden:      {summary.discovered}")
    print(f"Geselecteerd:  {summary.selected}")
    print(f"Nieuw:         {summary.created}")
    print(f"Gewijzigd:     {summary.changed}")
    print(f"Ongewijzigd:   {summary.unchanged}")
    print(f"Mislukt:       {summary.failed}")

    if summary.errors:
        print()
        print("Meldingen:")

        for error in summary.errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()