"""HTML-parsing voor openbare Flextender-opdrachten."""

import html
import re
from dataclasses import dataclass
from urllib.parse import (
    parse_qs,
    urljoin,
    urlparse,
)

from bs4 import BeautifulSoup

from backend.app.schemas.ingestion import (
    SourceOpportunityStatus,
)


CURRENT_DETAIL_PATTERN = re.compile(
    r"""
    (?P<url>
        https?://app\.flextender\.nl
        /nologin/jobdetails/\d+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

LEGACY_DETAIL_PATTERN = re.compile(
    r"""
    (?P<url>
        https?://(?:www\.)?flextender\.nl
        /opdracht/?\?
        [^"'<>]*aanvraagnr=\d+
        [^"'<>]*
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

CURRENT_PATH_PATTERN = re.compile(
    r"^/nologin/jobdetails/(?P<reference>\d+)/?$",
    re.IGNORECASE,
)

ALLOWED_HOSTS = {
    "flextender.nl",
    "www.flextender.nl",
    "app.flextender.nl",
}


@dataclass(frozen=True, slots=True)
class DiscoveredOpportunity:
    """Een op een overzichtspagina gevonden opdracht."""

    source_reference: str
    source_url: str


def extract_source_reference(
    url: str,
) -> str | None:
    """Haal het Flextender-aanvraagnummer uit een URL."""

    parsed_url = urlparse(url)
    hostname = (
        parsed_url.hostname or ""
    ).lower()

    if hostname not in ALLOWED_HOSTS:
        return None

    current_match = CURRENT_PATH_PATTERN.match(
        parsed_url.path
    )

    if current_match:
        return current_match.group("reference")

    if parsed_url.path.rstrip("/") == "/opdracht":
        query = parse_qs(parsed_url.query)
        references = query.get("aanvraagnr", [])

        if references:
            reference = references[0].strip()

            if reference.isdigit():
                return reference

    return None


def canonicalize_detail_url(
    url: str,
    source_reference: str,
) -> str:
    """Maak van een gevonden URL een stabiele detail-URL."""

    parsed_url = urlparse(url)
    hostname = (
        parsed_url.hostname or ""
    ).lower()

    if hostname == "app.flextender.nl":
        return (
            "https://app.flextender.nl/"
            f"nologin/jobdetails/{source_reference}"
        )

    return (
        "https://www.flextender.nl/"
        f"opdracht/?aanvraagnr={source_reference}"
    )


def discover_opportunities(
    *,
    page_html: str,
    page_url: str,
) -> list[DiscoveredOpportunity]:
    """Zoek huidige en oudere Flextender-detail-URL's."""

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    discovered: dict[
        str,
        DiscoveredOpportunity,
    ] = {}

    def add_candidate(candidate_url: str) -> None:
        cleaned_url = html.unescape(
            candidate_url.strip()
        ).rstrip("),.;")

        absolute_url = urljoin(
            page_url,
            cleaned_url,
        )

        source_reference = extract_source_reference(
            absolute_url
        )

        if source_reference is None:
            return

        if source_reference in discovered:
            return

        discovered[source_reference] = (
            DiscoveredOpportunity(
                source_reference=source_reference,
                source_url=canonicalize_detail_url(
                    absolute_url,
                    source_reference,
                ),
            )
        )

    # Normale links in de HTML.
    for link in soup.find_all(
        "a",
        href=True,
    ):
        add_candidate(str(link["href"]))

    # URL's die eventueel in scripts of JSON staan.
    for pattern in (
        CURRENT_DETAIL_PATTERN,
        LEGACY_DETAIL_PATTERN,
    ):
        for match in pattern.finditer(page_html):
            add_candidate(match.group("url"))

    return list(discovered.values())


def parse_title_hint(
    page_html: str,
) -> str | None:
    """Haal een bruikbare functietitel uit de detailpagina."""

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    excluded_titles = {
        "opdracht",
        "opdrachten",
        "flextender",
        "flextender office",
    }

    for heading in soup.find_all(
        ["h1", "h2", "h3"],
    ):
        title = heading.get_text(
            " ",
            strip=True,
        )

        if not title:
            continue

        if title.lower() in excluded_titles:
            continue

        if len(title) < 3:
            continue

        return title

    return None


def validate_detail_page(
    *,
    page_html: str,
    source_reference: str,
) -> None:
    """Controleer of dit werkelijk een Flextender-opdracht is."""

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    page_text = soup.get_text(
        " ",
        strip=True,
    )

    if "Aanvraagnummer" not in page_text:
        raise ValueError(
            "De detailpagina bevat geen aanvraagnummer."
        )

    if source_reference not in page_text:
        raise ValueError(
            "Het gevonden aanvraagnummer komt niet "
            "voor in de detailpagina."
        )


def detect_source_status(
    page_html: str,
) -> SourceOpportunityStatus:
    """Bepaal of reageren nog mogelijk lijkt."""

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    page_text = soup.get_text(
        " ",
        strip=True,
    ).lower()

    closed_indicators = (
        "reactietermijn verlopen",
        "reactietermijn is verlopen",
        "niet meer mogelijk te reageren",
        "termijn voor het indienen is verstreken",
    )

    if any(
        indicator in page_text
        for indicator in closed_indicators
    ):
        return "closed"

    return "active"