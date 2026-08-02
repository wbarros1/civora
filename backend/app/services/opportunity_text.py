"""Voorbewerking van ruwe opdracht-HTML voor extractie."""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Comment, Tag


REMOVABLE_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "button",
}

UNWRAP_TAGS = {
    "form",
}

PREFERRED_CONTENT_SELECTORS = (
    "[class*='jobdetail']",
    "[class*='job-detail']",
    "[class*='vacancy']",
    "[class*='opdracht']",
    "main",
    "article",
)

BLOCK_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "div",
    "section",
    "article",
    "li",
    "dt",
    "dd",
    "tr",
}


@dataclass(
    frozen=True,
    slots=True,
)
class PreparedOpportunityText:
    """Resultaat van HTML-voorbewerking."""

    text: str
    original_character_count: int
    prepared_character_count: int
    truncated: bool


def _is_hidden_element(
    element: Tag,
) -> bool:
    """Bepaal of een HTML-element visueel verborgen is."""

    attributes = getattr(
        element,
        "attrs",
        None,
    )

    if not isinstance(
        attributes,
        dict,
    ):
        return False

    if "hidden" in attributes:
        return True

    aria_hidden = attributes.get(
        "aria-hidden"
    )

    if (
        isinstance(aria_hidden, str)
        and aria_hidden.casefold() == "true"
    ):
        return True

    style_value = attributes.get(
        "style"
    )

    if isinstance(style_value, list):
        style_value = " ".join(
            str(value)
            for value in style_value
        )

    if not isinstance(style_value, str):
        return False

    normalized_style = re.sub(
        r"\s+",
        "",
        style_value.casefold(),
    )

    return (
        "display:none" in normalized_style
        or "visibility:hidden" in normalized_style
    )

def _remove_unwanted_content(
    soup: BeautifulSoup,
) -> None:
    """
    Verwijder niet-inhoudelijke en verborgen HTML.

    Formulieren worden alleen uitgepakt. De inhoud binnen het
    formulier blijft daardoor behouden.
    """

    for tag_name in REMOVABLE_TAGS:
        for element in list(
            soup.find_all(tag_name)
        ):
            element.decompose()

    for tag_name in UNWRAP_TAGS:
        for element in list(
            soup.find_all(tag_name)
        ):
            element.unwrap()

    for comment in list(
        soup.find_all(
            string=lambda value: isinstance(
                value,
                Comment,
            )
        )
    ):
        comment.extract()

    for element in list(
        soup.find_all(True)
    ):
        # Elementen die al zijn verwijderd kunnen nog tijdelijk
        # in de eerder opgebouwde lijst voorkomen.
        if element.parent is None:
            continue

        if _is_hidden_element(
            element
        ):
            element.decompose()


def _select_content_root(
    soup: BeautifulSoup,
) -> Tag | BeautifulSoup:
    """Selecteer bij voorkeur het inhoudelijke opdrachtgedeelte."""

    best_candidate: Tag | None = None
    best_length = 0

    for selector in PREFERRED_CONTENT_SELECTORS:
        for candidate in soup.select(
            selector
        ):
            candidate_text = candidate.get_text(
                " ",
                strip=True,
            )

            candidate_length = len(
                candidate_text
            )

            if candidate_length > best_length:
                best_candidate = candidate
                best_length = candidate_length

    if (
        best_candidate is not None
        and best_length >= 500
    ):
        return best_candidate

    if soup.body is not None:
        return soup.body

    return soup


def _insert_block_separators(
    root: Tag | BeautifulSoup,
) -> None:
    """Behoud globale sectie- en lijststructuur."""

    for element in root.find_all(
        BLOCK_TAGS
    ):
        element.insert_before("\n")
        element.insert_after("\n")


def _normalize_text(
    value: str,
) -> str:
    """Normaliseer witruimte zonder alle secties samen te voegen."""

    value = value.replace(
        "\xa0",
        " ",
    )

    normalized_lines: list[str] = []

    for line in value.splitlines():
        cleaned_line = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        if cleaned_line:
            normalized_lines.append(
                cleaned_line
            )

    deduplicated_lines: list[str] = []
    previous_line: str | None = None

    for line in normalized_lines:
        if line == previous_line:
            continue

        deduplicated_lines.append(
            line
        )
        previous_line = line

    return "\n".join(
        deduplicated_lines
    ).strip()


def prepare_opportunity_text(
    raw_html: str,
    *,
    max_characters: int = 60_000,
) -> PreparedOpportunityText:
    """Maak compacte, leesbare opdrachttekst voor extractie."""

    if max_characters < 1_000:
        raise ValueError(
            "max_characters moet minimaal 1000 zijn."
        )

    if not raw_html.strip():
        raise ValueError(
            "De ruwe HTML mag niet leeg zijn."
        )

    soup = BeautifulSoup(
        raw_html,
        "html.parser",
    )

    _remove_unwanted_content(
        soup
    )

    content_root = _select_content_root(
        soup
    )

    _insert_block_separators(
        content_root
    )

    prepared_text = _normalize_text(
        content_root.get_text(
            "\n",
            strip=True,
        )
    )

    if not prepared_text:
        raise ValueError(
            "Na HTML-voorbewerking bleef geen tekst over."
        )

    truncated = (
        len(prepared_text)
        > max_characters
    )

    if truncated:
        prepared_text = (
            prepared_text[
                :max_characters
            ].rstrip()
        )

    return PreparedOpportunityText(
        text=prepared_text,
        original_character_count=len(
            raw_html
        ),
        prepared_character_count=len(
            prepared_text
        ),
        truncated=truncated,
    )