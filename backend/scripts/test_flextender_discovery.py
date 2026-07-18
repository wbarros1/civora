"""Controleer de Flextender AJAX-discovery zonder opslag."""

from backend.app.connectors.flextender.client import (
    FlextenderHttpClient,
)
from backend.app.connectors.flextender.connector import (
    discover_flextender_opportunities,
)
from backend.app.core.config import get_settings


def main() -> None:
    """Toon het aantal ontdekte Flextender-opdrachten."""

    settings = get_settings()

    with FlextenderHttpClient(
        user_agent=settings.user_agent,
        timeout_seconds=(
            settings.request_timeout_seconds
        ),
    ) as client:
        opportunities = (
            discover_flextender_opportunities(
                client
            )
        )

    print()
    print("Flextender AJAX-discovery")
    print("-------------------------")
    print(
        f"Gevonden opdrachten: "
        f"{len(opportunities)}"
    )
    print()
    print("Eerste 10:")

    for (
        source_reference,
        source_url,
    ) in opportunities[:10]:
        print(
            f"- {source_reference}: "
            f"{source_url}"
        )


if __name__ == "__main__":
    main()