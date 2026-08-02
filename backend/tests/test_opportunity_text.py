"""Tests voor opdrachttekstvoorbewerking."""

from backend.app.services.opportunity_text import (
    prepare_opportunity_text,
)


def test_prepares_visible_opportunity_text() -> None:
    """Relevante zichtbare tekst blijft behouden."""

    raw_html = """
    <html>
        <body>
            <main>
                <h1>Senior Projectleider</h1>

                <section>
                    <h2>Opdrachtgever</h2>
                    <p>Gemeente Voorbeeld</p>
                </section>

                <section>
                    <h2>Eisen</h2>
                    <ul>
                        <li>Minimaal vijf jaar ervaring</li>
                        <li>Hbo werk- en denkniveau</li>
                    </ul>
                </section>
            </main>
        </body>
    </html>
    """

    result = prepare_opportunity_text(
        raw_html
    )

    assert "Senior Projectleider" in result.text
    assert "Gemeente Voorbeeld" in result.text
    assert "Minimaal vijf jaar ervaring" in result.text
    assert result.truncated is False


def test_removes_scripts_and_hidden_content() -> None:
    """Scripts en verborgen inhoud gaan niet naar het model."""

    raw_html = """
    <html>
        <body>
            <main>
                <h1>Adviseur Informatiebeheer</h1>
                <p>32 uur per week</p>

                <script>
                    dynamicTrackingId = "123";
                </script>

                <div style="display: none">
                    Verborgen interne tekst
                </div>

                <div aria-hidden="true">
                    Ook verborgen
                </div>
            </main>
        </body>
    </html>
    """

    result = prepare_opportunity_text(
        raw_html
    )

    assert "Adviseur Informatiebeheer" in result.text
    assert "32 uur per week" in result.text
    assert "dynamicTrackingId" not in result.text
    assert "Verborgen interne tekst" not in result.text
    assert "Ook verborgen" not in result.text


def test_truncates_large_content() -> None:
    """Zeer grote documenten worden begrensd."""

    raw_html = (
        "<html><body><main><p>"
        + ("Opdrachttekst " * 1000)
        + "</p></main></body></html>"
    )

    result = prepare_opportunity_text(
        raw_html,
        max_characters=1000,
    )

    assert result.truncated is True
    assert result.prepared_character_count <= 1000


def test_preserves_content_inside_form() -> None:
    """Inhoud binnen een formulier blijft behouden."""

    raw_html = """
    <html>
        <body>
            <form>
                <main>
                    <h1>Senior Projectleider</h1>
                    <p>Gemeente Rotterdam</p>
                    <p>36 uur per week</p>
                </main>
            </form>
        </body>
    </html>
    """

    result = prepare_opportunity_text(
        raw_html
    )

    assert "Senior Projectleider" in result.text
    assert "Gemeente Rotterdam" in result.text
    assert "36 uur per week" in result.text