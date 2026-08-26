"""Voorbereiding en verificatie van kandidaatprofiel-input."""

from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass
from typing import Iterator

from pydantic import BaseModel

from backend.app.schemas.candidate_profile import (
    CandidateProfile,
    EvidenceSnippet,
)
from backend.app.services.candidate_cv_text import (
    ExtractedCvText,
    ensure_readable_cv_text,
    normalize_cv_text,
)


MAX_CANDIDATE_PROFILE_INPUT_CHARACTERS = (
    120_000
)


class CandidateProfileInputError(
    ValueError
):
    """Basisklasse voor fouten in kandidaatprofiel-input."""


class CandidateProfileInputTooLargeError(
    CandidateProfileInputError
):
    """De CV-tekst is te groot voor veilige verwerking."""


@dataclass(
    frozen=True
)
class PreparedCandidateProfileInput:
    """Veilig voorbereide input voor kandidaatprofielextractie."""

    text: str

    input_sha256: str

    character_count: int

    readable_character_count: int

    line_count: int

    source_type: str

    page_count: (
        int
        | None
    )


@dataclass(
    frozen=True
)
class EvidenceVerificationResult:
    """Resultaat van verificatie tegen de CV-brontekst."""

    total_snippets: int

    verified_snippets: int

    missing_snippets: tuple[
        str,
        ...
    ]

    @property
    def is_valid(
        self,
    ) -> bool:
        """Alle evidence moet aantoonbaar in het CV staan."""

        return (
            self.total_snippets
            == self.verified_snippets
            and not self.missing_snippets
        )


def remove_unsafe_control_characters(
    value: str,
) -> str:
    """
    Verwijder controlekarakters die geen
    betekenisvolle CV-inhoud vertegenwoordigen.

    Nieuwe regels blijven behouden.
    """

    return "".join(
        character
        for character in value
        if (
            character == "\n"
            or ord(
                character
            ) >= 32
        )
    )


def prepare_candidate_profile_input(
    extracted_text: ExtractedCvText,
) -> PreparedCandidateProfileInput:
    """
    Maak deterministische, gehashte input
    voor de kandidaatprofielextractor.
    """

    safe_text = (
        remove_unsafe_control_characters(
            extracted_text.text
        )
    )

    safe_text = normalize_cv_text(
        safe_text
    )

    ensure_readable_cv_text(
        safe_text
    )

    character_count = len(
        safe_text
    )

    if (
        character_count
        > MAX_CANDIDATE_PROFILE_INPUT_CHARACTERS
    ):
        raise CandidateProfileInputTooLargeError(
            "Het CV bevat te veel tekst "
            "om veilig automatisch te verwerken."
        )

    input_sha256 = hashlib.sha256(
        safe_text.encode(
            "utf-8"
        )
    ).hexdigest()

    readable_character_count = len(
        re.sub(
            r"\s+",
            "",
            safe_text,
        )
    )

    line_count = len(
        safe_text.splitlines()
    )

    return PreparedCandidateProfileInput(
        text=safe_text,
        input_sha256=input_sha256,
        character_count=character_count,
        readable_character_count=(
            readable_character_count
        ),
        line_count=line_count,
        source_type=(
            extracted_text.source_type
        ),
        page_count=(
            extracted_text.page_count
        ),
    )


def normalize_evidence_comparison(
    value: str,
) -> str:
    """
    Normaliseer uitsluitend voor evidencevergelijking.

    Hoofdletters en witruimte mogen verschillen,
    maar woorden en inhoud niet.
    """

    normalized_value = (
        normalize_cv_text(
            value
        )
    )

    return " ".join(
        normalized_value.split()
    ).casefold()


def evidence_exists_in_source(
    *,
    source_text: str,
    evidence_text: str,
) -> bool:
    """
    Controleer of evidence als genormaliseerde
    letterlijke substring in de bron voorkomt.
    """

    source_comparison = (
        normalize_evidence_comparison(
            source_text
        )
    )

    evidence_comparison = (
        normalize_evidence_comparison(
            evidence_text
        )
    )

    if not evidence_comparison:
        return False

    return (
        evidence_comparison
        in source_comparison
    )


def iter_evidence_snippets(
    value: object,
) -> Iterator[
    EvidenceSnippet
]:
    """
    Vind EvidenceSnippet-objecten recursief
    in ieder kandidaatprofielobject.
    """

    if isinstance(
        value,
        EvidenceSnippet,
    ):
        yield value
        return

    if isinstance(
        value,
        BaseModel,
    ):
        for field_name in (
            type(
                value
            ).model_fields
        ):
            field_value = getattr(
                value,
                field_name,
            )

            yield from (
                iter_evidence_snippets(
                    field_value
                )
            )

        return

    if isinstance(
        value,
        dict,
    ):
        for item in value.values():
            yield from (
                iter_evidence_snippets(
                    item
                )
            )

        return

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        for item in value:
            yield from (
                iter_evidence_snippets(
                    item
                )
            )


def verify_candidate_profile_evidence(
    *,
    profile: CandidateProfile,
    source_text: str,
) -> EvidenceVerificationResult:
    """
    Verifieer ieder evidencefragment uit een
    kandidaatprofiel tegen de echte CV-brontekst.
    """

    source_comparison = (
        normalize_evidence_comparison(
            source_text
        )
    )

    unique_snippets: list[str] = []

    seen_snippets: set[str] = set()

    for snippet in (
        iter_evidence_snippets(
            profile
        )
    ):
        comparison_value = (
            normalize_evidence_comparison(
                snippet.text
            )
        )

        if (
            not comparison_value
            or comparison_value
            in seen_snippets
        ):
            continue

        seen_snippets.add(
            comparison_value
        )

        unique_snippets.append(
            snippet.text
        )

    verified_snippets = 0

    missing_snippets: list[str] = []

    for snippet_text in unique_snippets:
        snippet_comparison = (
            normalize_evidence_comparison(
                snippet_text
            )
        )

        if (
            snippet_comparison
            in source_comparison
        ):
            verified_snippets += 1

            continue

        missing_snippets.append(
            snippet_text
        )

    return EvidenceVerificationResult(
        total_snippets=len(
            unique_snippets
        ),
        verified_snippets=(
            verified_snippets
        ),
        missing_snippets=tuple(
            missing_snippets
        ),
    )