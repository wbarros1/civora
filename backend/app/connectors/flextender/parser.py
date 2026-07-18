"""HTML-parsing voor openbare Flextender-opdrachten."""

import html
import re
from typing import Any
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

FLEXTENDER_DETAIL_BASE_URL = (
    "https://app.flextender.nl/nologin/jobdetails"
)

FLEXTENDER_REFERENCE_PATTERN = re.compile(
    r"""
    (?:
        /nologin/jobdetails/
        |
        jobdetails/
        |
        aanvraagnr=
    )
    (?P<reference>\d+)
    """,
    re.IGNORECASE | re.VERBOSE,
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

def parse_widget_config(
    page_html: str,
) -> str:
    """Haal de Flextender-widgetconfiguratie uit de opdrachtenpagina."""

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    config_element = soup.select_one(
        '[name="kbs_flx_widget_config"]'
    )

    if config_element is not None:
        attributes = getattr(
            config_element,
            "attrs",
            None,
        )

        if isinstance(attributes, dict):
            value = attributes.get("value")

            if isinstance(value, str) and value.strip():
                return html.unescape(
                    value
                ).strip()

        element_text = config_element.get_text(
            strip=True,
        )

        if element_text:
            return html.unescape(
                element_text
            ).strip()

    fallback_patterns = (
        re.compile(
            r"""
            name=["']kbs_flx_widget_config["']
            [^>]*?
            value=["'](?P<value>[^"']+)["']
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
        re.compile(
            r"""
            value=["'](?P<value>[^"']+)["']
            [^>]*?
            name=["']kbs_flx_widget_config["']
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    )

    for pattern in fallback_patterns:
        match = pattern.search(page_html)

        if match is not None:
            return html.unescape(
                match.group("value")
            ).strip()

    raise ValueError(
        "kbs_flx_widget_config is niet gevonden "
        "in de Flextender-opdrachtenpagina."
    )

def parse_search_result_html(
    response_data: Any,
) -> str:
    """Haal resultHtml veilig uit de Flextender AJAX-response."""

    if not isinstance(response_data, dict):
        raise ValueError(
            "De Flextender AJAX-response is geen object."
        )

    result_html = response_data.get(
        "resultHtml"
    )

    if not isinstance(result_html, str):
        raise ValueError(
            "De Flextender AJAX-response bevat geen "
            "geldige resultHtml-waarde."
        )

    if not result_html.strip():
        raise ValueError(
            "De Flextender AJAX-response bevat lege resultHtml."
        )

    return result_html

def parse_listing_references(
    result_html: str,
) -> list[str]:
    """
    Haal unieke aanvraagreferenties uit resultHtml.

    De volgorde uit de Flextender-resultatenlijst blijft behouden.
    """

    normalized_html = html.unescape(
        result_html
    ).replace(
        r"\/",
        "/",
    )

    references: list[str] = []
    seen_references: set[str] = set()

    for match in FLEXTENDER_REFERENCE_PATTERN.finditer(
        normalized_html
    ):
        source_reference = match.group(
            "reference"
        )

        if source_reference in seen_references:
            continue

        seen_references.add(
            source_reference
        )
        references.append(
            source_reference
        )

    return references

def build_detail_url(
    source_reference: str,
) -> str:
    """Bouw de vaste Flextender-detail-URL."""

    cleaned_reference = (
        source_reference.strip()
    )

    if not cleaned_reference.isdigit():
        raise ValueError(
            "Een Flextender-referentie moet numeriek zijn."
        )

    return (
        f"{FLEXTENDER_DETAIL_BASE_URL}/"
        f"{cleaned_reference}"
    )

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

def _normalize_title_candidate(
    value: str,
) -> str | None:
    """Maak een mogelijke Flextender-functietitel schoon."""

    candidate = re.sub(
        r"\s+",
        " ",
        html.unescape(value),
    ).strip()

    if not candidate:
        return None

    generic_titles = {
        "opdracht",
        "opdrachten",
        "flextender",
        "flextender office",
        "flextender office - flextender",
    }

    if candidate.lower() in generic_titles:
        return None

    flextender_suffixes = (
        " | Flextender",
        " - Flextender",
    )

    for suffix in flextender_suffixes:
        if candidate.endswith(suffix):
            candidate = candidate[
                :-len(suffix)
            ].strip()

    if candidate.lower() in generic_titles:
        return None

    return candidate or None

def _parse_title_from_assignment_block(
    soup: BeautifulSoup,
) -> str | None:
    """
    Zoek de titel tussen 'Opdracht' en 'Aanvraagnummer'.

    Op Flextender staat hier doorgaans:
    Opdracht → functietitel → opdrachtgever → Aanvraagnummer.
    """

    text_parts = [
        re.sub(
            r"\s+",
            " ",
            text,
        ).strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    for reference_index, text in enumerate(
        text_parts
    ):
        if text.lower() != "aanvraagnummer":
            continue

        for index in range(
            reference_index - 1,
            -1,
            -1,
        ):
            if text_parts[index].lower() != "opdracht":
                continue

            candidates = text_parts[
                index + 1:reference_index
            ]

            for candidate in candidates:
                normalized_candidate = (
                    _normalize_title_candidate(
                        candidate
                    )
                )

                if normalized_candidate:
                    return normalized_candidate

            break

    return None

def _parse_title_from_metadata(
    soup: BeautifulSoup,
) -> str | None:
    """Haal een titel veilig uit Open Graph- of Twittermetadata."""

    metadata_selectors = (
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
    )

    for selector in metadata_selectors:
        element = soup.select_one(selector)

        if element is None:
            continue

        attributes = getattr(
            element,
            "attrs",
            None,
        ) or {}

        content = attributes.get("content")

        if not isinstance(content, str):
            continue

        candidate = _normalize_title_candidate(
            content
        )

        if candidate is None:
            continue

        if " - " in candidate:
            candidate = candidate.rsplit(
                " - ",
                1,
            )[0].strip()

        return _normalize_title_candidate(
            candidate
        )

    return None

def _parse_title_from_document_title(
    soup: BeautifulSoup,
) -> str | None:
    """Gebruik het HTML-title-element als laatste fallback."""

    title_element = soup.find("title")

    if title_element is None:
        return None

    title_text = title_element.get_text(
        " ",
        strip=True,
    )

    candidate = _normalize_title_candidate(
        title_text
    )

    if candidate is None:
        return None

    if " - " in candidate:
        candidate = candidate.rsplit(
            " - ",
            1,
        )[0].strip()

    return _normalize_title_candidate(
        candidate
    )

def parse_title_hint(
    page_html: str,
) -> str | None:
    """Haal een bruikbare functietitel uit de detailpagina."""

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    assignment_title = (
        _parse_title_from_assignment_block(
            soup
        )
    )

    if assignment_title:
        return assignment_title

    for heading in soup.find_all(
        ["h1", "h2", "h3"],
    ):
        candidate = _normalize_title_candidate(
            heading.get_text(
                " ",
                strip=True,
            )
        )

        if candidate:
            return candidate

    metadata_title = _parse_title_from_metadata(
        soup
    )

    if metadata_title:
        return metadata_title

    return _parse_title_from_document_title(
        soup
    )

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