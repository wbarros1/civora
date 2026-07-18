"""Tests voor de Flextender HTML-parser."""

import pytest

from backend.app.connectors.flextender.parser import (
    detect_source_status,
    discover_opportunities,
    parse_title_hint,
    validate_detail_page,
    build_detail_url,
    parse_listing_references,
    parse_search_result_html,
    parse_widget_config,
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

def test_parses_title_from_assignment_block() -> None:
    """Haal de titel tussen Opdracht en Aanvraagnummer op."""

    page_html = """
    <html>
        <body>
            <div>Opdracht</div>
            <div>Azure Netwerk Engineer</div>
            <div>Kadaster</div>
            <div>Aanvraagnummer</div>
            <div>30335</div>
        </body>
    </html>
    """

    assert (
        parse_title_hint(page_html)
        == "Azure Netwerk Engineer"
    )


def test_parses_title_from_metadata() -> None:
    """Gebruik Open Graph als de opdrachtsectie ontbreekt."""

    page_html = """
    <html>
        <head>
            <meta
                property="og:title"
                content="
                    Senior Beleidsadviseur OOV
                    - Gemeente Midden-Delfland
                "
            >
        </head>
        <body></body>
    </html>
    """

    assert (
        parse_title_hint(page_html)
        == "Senior Beleidsadviseur OOV"
    )


def test_ignores_generic_document_title() -> None:
    """Een algemene Flextender-titel is geen functietitel."""

    page_html = """
    <html>
        <head>
            <title>
                Flextender Office - Flextender
            </title>
        </head>
        <body></body>
    </html>
    """

    assert parse_title_hint(page_html) is None

def test_metadata_parser_handles_missing_content() -> None:
    """Een meta-element zonder content mag geen fout veroorzaken."""

    page_html = """
    <html>
        <head>
            <meta property="og:title">
            <meta
                name="twitter:title"
                content="
                    Senior Beleidsadviseur OOV
                    - Gemeente Midden-Delfland
                "
            >
        </head>
        <body></body>
    </html>
    """

    assert (
        parse_title_hint(page_html)
        == "Senior Beleidsadviseur OOV"
    )


def test_title_parser_handles_missing_metadata() -> None:
    """Ontbrekende metadata geeft netjes None terug."""

    page_html = """
    <html>
        <head></head>
        <body>
            <p>Geen functietitel aanwezig</p>
        </body>
    </html>
    """

    assert parse_title_hint(page_html) is None

def test_parse_widget_config() -> None:
    """Haal de versleutelde widgetconfiguratie uit HTML."""

    page_html = """
    <form>
        <input
            type="hidden"
            name="kbs_flx_widget_config"
            value="ABC123XYZ"
        >
    </form>
    """

    assert (
        parse_widget_config(page_html)
        == "ABC123XYZ"
    )


def test_parse_search_result_html() -> None:
    """Lees resultHtml uit de AJAX-response."""

    response_data = {
        "resultHtml": "<div>Resultaten</div>",
    }

    assert (
        parse_search_result_html(
            response_data
        )
        == "<div>Resultaten</div>"
    )


def test_parse_listing_references() -> None:
    """Lees unieke referenties en behoud hun volgorde."""

    result_html = """
    <a href="/nologin/jobdetails/30959">
        Eerste opdracht
    </a>

    <a href="https:\\/\\/app.flextender.nl\\/nologin\\/jobdetails\\/30841">
        Tweede opdracht
    </a>

    <a href="/nologin/jobdetails/30959">
        Dubbele eerste opdracht
    </a>

    <a href="/opdracht/?aanvraagnr=30740">
        Derde opdracht
    </a>
    """

    assert parse_listing_references(
        result_html
    ) == [
        "30959",
        "30841",
        "30740",
    ]


def test_build_detail_url() -> None:
    """Bouw de vaste app.flextender.nl-detail-URL."""

    assert build_detail_url(
        "30959"
    ) == (
        "https://app.flextender.nl/"
        "nologin/jobdetails/30959"
    )