"""Deterministische controle en nabewerking van LLM-extracties."""

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.schemas.opportunity_extraction import (
    OpportunityExtractionEnvelope,
)


AMSTERDAM_TIMEZONE = ZoneInfo(
    "Europe/Amsterdam"
)

MAXIMUM_RATE_PATTERNS = (
    re.compile(
        r"\bmaximum\s+uurtarief\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmaximaal(?:\s+uurtarief)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\buurtarief\s+van\s+maximaal\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btarief\s+is\s+maximaal\b",
        re.IGNORECASE,
    ),
)

NON_ACTIONABLE_REVIEW_TERMS = (
    # Ontbrekende optionele velden.
    "number of positions",
    "aantal posities",
    "aantal kandidaten",
    "publication date",
    "publicatiedatum",
    "duration_months",
    "duration months",
    "duur in maanden",

    # Correcte interpretatie van minimum- en maximumtarieven.
    "geen expliciet minimumtarief",
    "tarief vermeld als maximaal",
    "alleen een maximumtarief",
    "uitsluitend een maximumtarief",

    # Correcte interpretatie van de contractvorm.
    "employment_relationship gezet op",
    "employment relationship gezet op",
    "employment_relationship op basis van",
    "employment relationship op basis van",
    "geïnterpreteerd als 'secondment'",
    'geïnterpreteerd als "secondment"',
    "geinterpreteerd als 'secondment'",
    'geinterpreteerd als "secondment"',
    "vereiste driepartijen detachering",
    "verplichte detachering en arbeidsovereenkomst",

    # Algemeen voorbehoud bij een concrete startdatum.
    "startdatum vermeld 'onder voorbehoud'",
    'startdatum vermeld "onder voorbehoud"',
    "startdatum is onder voorbehoud",
    "concrete datum is opgenomen",
    "mogelijke verschuiving niet verder gespecificeerd",

        # Alternatieve formuleringen voor contractcategorisatie.
    "employment_relationship gekozen als",
    "employment relationship gekozen als",
    "employment_relationship geïnterpreteerd als",
    "employment relationship geïnterpreteerd als",
    "detacherings- en driepartijenovereenkomst verplicht",

    # Ontbrekend optioneel aantal posities.
    "number_of_positions ontbreekt",
    "number of positions ontbreekt",
    "aantal posities ontbreekt",
    "aantal kandidaten ontbreekt",
)


@dataclass(
    frozen=True,
    slots=True,
)
class PostProcessedExtraction:
    """Gecontroleerd extractieresultaat."""

    extraction: OpportunityExtractionEnvelope
    application_status: str
    review_required: bool
    corrections: tuple[str, ...]


def derive_application_status(
    *,
    source_status: str,
    application_deadline: datetime | None,
    current_time: datetime | None = None,
) -> str:
    """Bepaal of nog op de opdracht gereageerd kan worden."""

    if source_status == "closed":
        return "closed"

    if application_deadline is None:
        return "unknown"

    comparison_time = (
        current_time
        if current_time is not None
        else datetime.now(
            AMSTERDAM_TIMEZONE
        )
    )

    normalized_deadline = (
        application_deadline
    )

    if normalized_deadline.tzinfo is None:
        normalized_deadline = (
            normalized_deadline.replace(
                tzinfo=AMSTERDAM_TIMEZONE
            )
        )

    if comparison_time.tzinfo is None:
        comparison_time = (
            comparison_time.replace(
                tzinfo=AMSTERDAM_TIMEZONE
            )
        )

    if normalized_deadline <= comparison_time:
        return "expired"

    if source_status == "active":
        return "open"

    return "unknown"


def _normalize_phone(
    value: str,
) -> str:
    """Houd alleen cijfers uit een telefoonnummer over."""

    return "".join(
        character
        for character in value
        if character.isdigit()
    )


def _build_contact_window(
    *,
    prepared_text: str,
    contact_name: str | None,
    contact_email: str | None,
) -> str:
    """Selecteer tekst rondom naam of e-mailadres."""

    normalized_text = (
        prepared_text.casefold()
    )

    positions: list[int] = []

    for value in (
        contact_name,
        contact_email,
    ):
        if not value:
            continue

        position = normalized_text.find(
            value.casefold()
        )

        if position >= 0:
            positions.append(
                position
            )

    if not positions:
        return prepared_text[:1500]

    first_position = min(
        positions
    )

    start = max(
        0,
        first_position - 300,
    )

    end = min(
        len(prepared_text),
        first_position + 1000,
    )

    return prepared_text[
        start:end
    ]


def _phone_is_supported(
    *,
    phone: str,
    contact_window: str,
) -> bool:
    """Controleer of het telefoonnummer in de contactsectie staat."""

    expected_digits = _normalize_phone(
        phone
    )

    if len(expected_digits) < 7:
        return False

    candidates = re.findall(
        r"\+?\d[\d\s()./-]{5,}\d",
        contact_window,
    )

    return any(
        _normalize_phone(candidate)
        == expected_digits
        for candidate in candidates
    )

def _mentions_maximum_rate(
    prepared_text: str,
) -> bool:
    """Controleer of de bron alleen over een maximumtarief spreekt."""

    return any(
        pattern.search(prepared_text)
        is not None
        for pattern in MAXIMUM_RATE_PATTERNS
    )


def _is_non_actionable_review_reason(
    reason: str,
) -> bool:
    """Herken meldingen over ontbrekende optionele velden."""

    normalized_reason = (
        reason.casefold()
    )

    return any(
        term in normalized_reason
        for term in NON_ACTIONABLE_REVIEW_TERMS
    )


def post_process_extraction(
    *,
    extraction: OpportunityExtractionEnvelope,
    prepared_text: str,
    title_hint: str | None,
    source_status: str,
    current_time: datetime | None = None,
) -> PostProcessedExtraction:
    """Pas brongebaseerde correcties en controles toe."""

    corrections: list[str] = []

    opportunity = (
        extraction.opportunity
    )

    opportunity_updates: dict[
        str,
        object,
    ] = {}

    cleaned_title_hint = (
        title_hint.strip()
        if isinstance(
            title_hint,
            str,
        )
        else ""
    )

    if (
        cleaned_title_hint
        and opportunity.title
        != cleaned_title_hint
    ):
        opportunity_updates[
            "title"
        ] = cleaned_title_hint

        corrections.append(
            "Titel genormaliseerd op basis "
            "van de betrouwbare title_hint."
        )

    contact = (
        opportunity.contact_information
    )

    contact_updates: dict[
        str,
        str | None,
    ] = {}

    normalized_prepared_text = (
        prepared_text.casefold()
    )

    if (
        opportunity.rate_min is not None
        and opportunity.rate_max is not None
        and opportunity.rate_min
        == opportunity.rate_max
        and _mentions_maximum_rate(
            prepared_text
        )
    ):
        opportunity_updates[
            "rate_min"
        ] = None

        corrections.append(
            "Minimumtarief verwijderd omdat "
            "de bron uitsluitend een "
            "maximumtarief vermeldt."
        )

    if (
        contact.name
        and contact.name.casefold()
        not in normalized_prepared_text
    ):
        contact_updates["name"] = None

        corrections.append(
            "Contactnaam verwijderd omdat deze "
            "niet letterlijk in de bron stond."
        )

    if (
        contact.email
        and contact.email.casefold()
        not in normalized_prepared_text
    ):
        contact_updates["email"] = None

        corrections.append(
            "Contact-e-mailadres verwijderd omdat "
            "dit niet letterlijk in de bron stond."
        )

    contact_window = _build_contact_window(
        prepared_text=prepared_text,
        contact_name=contact.name,
        contact_email=contact.email,
    )

    if (
        contact.phone
        and not _phone_is_supported(
            phone=contact.phone,
            contact_window=contact_window,
        )
    ):
        contact_updates["phone"] = None

        corrections.append(
            "Contacttelefoon verwijderd omdat deze "
            "niet aantoonbaar bij de contactsectie stond."
        )

    if contact_updates:
        opportunity_updates[
            "contact_information"
        ] = contact.model_copy(
            update=contact_updates
        )

    if opportunity_updates:
        opportunity = opportunity.model_copy(
            update=opportunity_updates
        )

    application_status = (
        derive_application_status(
            source_status=source_status,
            application_deadline=(
                opportunity
                .application_deadline
            ),
            current_time=current_time,
        )
    )

    deterministic_review_reasons: list[
        str
    ] = []

    if extraction.overall_confidence < 0.75:
        deterministic_review_reasons.append(
            "De overall confidence is lager dan 0,75."
        )

    if not opportunity.client_name:
        deterministic_review_reasons.append(
            "Opdrachtgever ontbreekt."
        )

    if opportunity.application_deadline is None:
        deterministic_review_reasons.append(
            "Reactiedeadline ontbreekt."
        )

    if opportunity.hours_per_week_max is None:
        deterministic_review_reasons.append(
            "Uren per week ontbreken."
        )

    combined_review_reasons: list[str] = []
    seen_reasons: set[str] = set()

    for reason in [
        *extraction.review_reasons,
        *deterministic_review_reasons,
    ]:
        normalized_reason = " ".join(
            reason.split()
        ).strip()

        if not normalized_reason:
            continue

        if _is_non_actionable_review_reason(
            normalized_reason
        ):
            continue

        comparison_value = (
            normalized_reason.casefold()
        )

        if comparison_value in seen_reasons:
            continue

        seen_reasons.add(
            comparison_value
        )

        combined_review_reasons.append(
            normalized_reason
        )

    updated_extraction = (
        extraction.model_copy(
            update={
                "opportunity": opportunity,
                "review_reasons": (
                    combined_review_reasons
                ),
            }
        )
    )

    return PostProcessedExtraction(
        extraction=updated_extraction,
        application_status=(
            application_status
        ),
        review_required=bool(
            combined_review_reasons
        ),
        corrections=tuple(
            corrections
        ),
    )