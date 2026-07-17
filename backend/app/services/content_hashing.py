"""Hulpfuncties voor wijzigingsdetectie."""

import hashlib
import html
import json
import re

from bs4 import BeautifulSoup, Comment

from backend.app.schemas.ingestion import RawFormat


WHITESPACE_PATTERN = re.compile(r"\s+")


def calculate_content_hash(content: str) -> str:
    """Bereken een SHA-256-hash van de exact ontvangen inhoud."""

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def normalize_whitespace(content: str) -> str:
    """Vervang opeenvolgende witruimte door één spatie."""

    return WHITESPACE_PATTERN.sub(
        " ",
        content,
    ).strip()


def normalize_html_content(content: str) -> str:
    """
    Maak een stabiele tekstrepresentatie van HTML.

    Scripts, stijlen, comments, verborgen invoervelden en andere
    niet-zichtbare elementen worden niet meegenomen.
    """

    soup = BeautifulSoup(
        content,
        "html.parser",
    )

    for element in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "canvas",
        ]
    ):
        element.decompose()

    for comment in soup.find_all(
        string=lambda text: isinstance(
            text,
            Comment,
        )
    ):
        comment.extract()

    hidden_elements = list(
        soup.select(
            (
                "[hidden], "
                '[aria-hidden="true"], '
                'input[type="hidden"]'
            )
        )
    )

    for element in hidden_elements:
        if getattr(element, "parent", None) is None:
            continue

        element.decompose()

    styled_elements = list(
        soup.find_all(style=True)
    )

    for element in styled_elements:
        attributes = getattr(
            element,
            "attrs",
            None,
        )

        if not isinstance(attributes, dict):
            continue

        style_attribute = attributes.get(
            "style"
        )

        if not isinstance(style_attribute, str):
            continue

        style_value = normalize_whitespace(
            style_attribute
        ).replace(
            " ",
            "",
        ).lower()

        if (
            "display:none" in style_value
            or "visibility:hidden" in style_value
        ):
            element.decompose()

    visible_text = soup.get_text(
        separator=" ",
        strip=True,
    )

    return normalize_whitespace(
        html.unescape(visible_text)
    )


def normalize_json_content(content: str) -> str:
    """Maak een JSON-document onafhankelijk van inspringing."""

    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError:
        return normalize_whitespace(content)

    return json.dumps(
        parsed_content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def normalize_content(
    *,
    content: str,
    raw_format: RawFormat,
) -> str:
    """Maak een stabiele inhoudsrepresentatie per bronformaat."""

    if raw_format == "html":
        return normalize_html_content(content)

    if raw_format == "json":
        return normalize_json_content(content)

    return normalize_whitespace(content)


def calculate_normalized_content_hash(
    *,
    content: str,
    raw_format: RawFormat,
) -> str:
    """Bereken de hash van de genormaliseerde inhoud."""

    normalized_content = normalize_content(
        content=content,
        raw_format=raw_format,
    )

    return calculate_content_hash(
        normalized_content
    )