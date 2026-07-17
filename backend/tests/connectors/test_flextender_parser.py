"""Tests voor de Flextender HTML-parser."""

import pytest

from backend.app.connectors.flextender.parser import (
    detect_source_status,
    discover_opportunities,
    parse_title_hint,
    validate_detail_page,
)


def test_discovers_current_and_legacy_urls() -> None:
    """Herken beide Flextender-detailformaten."""

    page_html = """
    <html>
        <body>
            <a href="
                https://app.flextender.nl/
                nologin/jobdetails/30335
            ">
                Huidige opdracht
            </a>

            <a href="
                https://www.flextender.nl/
                opdracht/?aanvraagnr=14499
                &resultatenlijst=ABC
            ">
                Oudere opdracht
            </a>
        </body>
    </html>
    """.replace("\n", "").replace(" ", "")

    opportunities = discover_opportunities(
        page_html=page_html,
        page_url="https://www.flextender.nl/",
    )

    assert [
        opportunity.source_reference
        for opportunity in opportunities
    ] == [
        "30335",
        "14499",
    ]


def test_parses_title_hint() -> None:
    """Haal de eerste bruikbare titel op."""

    page_html = """
    <html>
        <body>
            <main>
                <h1>Azure Netwerk Engineer</h1>
                <p>Kadaster</p>
                <p>Aanvraagnummer</p>
                <p>30335</p>
            </main>
        </body>
    </html>
    """

    assert (
        parse_title_hint(page_html)
        == "Azure Netwerk Engineer"
    )


def test_validates_detail_page() -> None:
    """Een geldige pagina bevat label en nummer."""

    page_html = """
    <html>
        <body>
            <p>Aanvraagnummer</p>
            <p>30335</p>
        </body>
    </html>
    """

    validate_detail_page(
        page_html=page_html,
        source_reference="30335",
    )


def test_rejects_wrong_detail_page() -> None:
    """Een algemene pagina is geen opdracht."""

    with pytest.raises(ValueError):
        validate_detail_page(
            page_html="<html><body>Homepage</body></html>",
            source_reference="30335",
        )


def test_detects_closed_opportunity() -> None:
    """Een verlopen reactietermijn wordt gesloten."""

    page_html = """
    <html>
        <body>
            Helaas is de reactietermijn verlopen
            en is het niet meer mogelijk te reageren.
        </body>
    </html>
    """

    assert detect_source_status(page_html) == "closed"