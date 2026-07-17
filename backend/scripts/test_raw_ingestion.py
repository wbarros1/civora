"""Test de volledige opslagketen voor ruwe brondata."""

from collections import Counter
from uuid import uuid4

from backend.app.repositories.ingestion import (
    create_fetch_run,
    finish_fetch_run,
    store_raw_opportunity,
)
from backend.app.repositories.sources import get_source_by_code


def main() -> None:
    """Voer een lokale ingestion-test uit."""

    source = get_source_by_code("flextender")

    fetch_run = create_fetch_run(
        source_id=source.id,
        triggered_by="manual",
        request_url=source.base_url,
        metadata={
            "test_run": True,
            "description": "Lokale opslagtest",
        },
    )

    source_reference = f"local-test-{uuid4()}"

    html_version_1 = """
    <html>
        <body>
            <h1>Senior Projectleider Gebiedsontwikkeling</h1>
            <p>Gemeente Voorbeeld</p>
            <p>32 uur per week</p>
        </body>
    </html>
    """.strip()

    html_version_2 = """
    <html>
        <body>
            <h1>Senior Projectleider Gebiedsontwikkeling</h1>
            <p>Gemeente Voorbeeld</p>
            <p>36 uur per week</p>
            <p>Maximaal tarief: 115 euro</p>
        </body>
    </html>
    """.strip()

    results = []

    results.append(
        store_raw_opportunity(
            source_id=source.id,
            fetch_run_id=fetch_run.id,
            source_reference=source_reference,
            source_url=(
                "https://www.flextender.nl/"
                f"opdracht/{source_reference}"
            ),
            title_hint=(
                "Senior Projectleider "
                "Gebiedsontwikkeling"
            ),
            raw_content=html_version_1,
            raw_format="html",
            metadata={
                "test_data": True,
            },
        )
    )

    results.append(
        store_raw_opportunity(
            source_id=source.id,
            fetch_run_id=fetch_run.id,
            source_reference=source_reference,
            source_url=(
                "https://www.flextender.nl/"
                f"opdracht/{source_reference}"
            ),
            title_hint=(
                "Senior Projectleider "
                "Gebiedsontwikkeling"
            ),
            raw_content=html_version_1,
            raw_format="html",
            metadata={
                "test_data": True,
            },
        )
    )

    results.append(
        store_raw_opportunity(
            source_id=source.id,
            fetch_run_id=fetch_run.id,
            source_reference=source_reference,
            source_url=(
                "https://www.flextender.nl/"
                f"opdracht/{source_reference}"
            ),
            title_hint=(
                "Senior Projectleider "
                "Gebiedsontwikkeling"
            ),
            raw_content=html_version_2,
            raw_format="html",
            metadata={
                "test_data": True,
            },
        )
    )

    action_counts = Counter(
        result.action
        for result in results
    )

    completed_run = finish_fetch_run(
        fetch_run_id=fetch_run.id,
        source_id=source.id,
        status="succeeded",
        http_status=200,
        items_discovered=len(results),
        items_new=action_counts["created"],
        items_changed=action_counts["changed"],
        items_unchanged=action_counts["unchanged"],
        items_failed=0,
        metadata={
            "test_run": True,
            "source_reference": source_reference,
        },
    )

    print()
    print("Ingestion-test voltooid")
    print("-------------------------")
    print(f"Bron:             {source.name}")
    print(f"Fetch run:        {completed_run.id}")
    print(f"Bronreferentie:   {source_reference}")
    print(f"Nieuwe records:   {completed_run.items_new}")
    print(f"Gewijzigd:        {completed_run.items_changed}")
    print(f"Ongewijzigd:      {completed_run.items_unchanged}")
    print(f"Mislukt:          {completed_run.items_failed}")
    print()

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"Actie {index}: "
            f"{result.action} "
            f"(versie {result.version_number})"
        )


if __name__ == "__main__":
    main()