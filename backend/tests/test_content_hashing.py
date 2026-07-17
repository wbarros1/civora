"""Tests voor inhoudelijke wijzigingsdetectie."""

from backend.app.services.content_hashing import (
    calculate_content_hash,
    calculate_normalized_content_hash,
    normalize_html_content,
)


def test_exact_hash_changes_for_dynamic_scripts() -> None:
    """De exacte HTML-hash ziet technische verschillen."""

    html_version_1 = """
    <html>
        <body>
            <main>
                <h1>Projectleider</h1>
            </main>
            <script>
                window.requestId = "abc";
            </script>
        </body>
    </html>
    """

    html_version_2 = """
    <html>
        <body>
            <main>
                <h1>Projectleider</h1>
            </main>
            <script>
                window.requestId = "xyz";
            </script>
        </body>
    </html>
    """

    assert (
        calculate_content_hash(html_version_1)
        != calculate_content_hash(html_version_2)
    )


def test_normalized_hash_ignores_dynamic_scripts() -> None:
    """Dynamische scripts veroorzaken geen inhoudelijke wijziging."""

    html_version_1 = """
    <html>
        <body>
            <main>
                <h1>Projectleider</h1>
                <p>32 uur per week</p>
            </main>
            <script>
                window.requestId = "abc";
            </script>
        </body>
    </html>
    """

    html_version_2 = """
    <html>
        <body data-session-id="anders">
            <main>
                <h1>Projectleider</h1>
                <p>
                    32 uur per week
                </p>
            </main>
            <script>
                window.requestId = "xyz";
            </script>
        </body>
    </html>
    """

    hash_version_1 = (
        calculate_normalized_content_hash(
            content=html_version_1,
            raw_format="html",
        )
    )

    hash_version_2 = (
        calculate_normalized_content_hash(
            content=html_version_2,
            raw_format="html",
        )
    )

    assert hash_version_1 == hash_version_2


def test_normalized_hash_detects_visible_change() -> None:
    """Een inhoudelijke wijziging geeft een andere hash."""

    html_version_1 = """
    <main>
        <h1>Projectleider</h1>
        <p>32 uur per week</p>
    </main>
    """

    html_version_2 = """
    <main>
        <h1>Projectleider</h1>
        <p>36 uur per week</p>
    </main>
    """

    hash_version_1 = (
        calculate_normalized_content_hash(
            content=html_version_1,
            raw_format="html",
        )
    )

    hash_version_2 = (
        calculate_normalized_content_hash(
            content=html_version_2,
            raw_format="html",
        )
    )

    assert hash_version_1 != hash_version_2


def test_hidden_content_is_removed() -> None:
    """Verborgen technische inhoud telt niet mee."""

    page_html = """
    <main>
        <h1>Adviseur</h1>
        <input
            type="hidden"
            value="wisselend-token"
        >
        <div aria-hidden="true">
            Verborgen tekst
        </div>
    </main>
    """

    normalized_content = normalize_html_content(
        page_html
    )

    assert normalized_content == "Adviseur"

def test_nested_hidden_and_styled_elements_do_not_fail() -> None:
    """Geneste verborgen elementen mogen de parser niet laten crashen."""

    page_html = """
    <html>
        <body>
            <main>
                <h1>Senior Beleidsadviseur OOV</h1>

                <div hidden>
                    <span style="display: none;">
                        Verborgen technische inhoud
                    </span>
                </div>

                <section style="visibility: hidden;">
                    Nog meer verborgen tekst
                </section>

                <p>32 uur per week</p>
            </main>
        </body>
    </html>
    """

    normalized_content = normalize_html_content(
        page_html
    )

    assert (
        normalized_content
        == "Senior Beleidsadviseur OOV 32 uur per week"
    )