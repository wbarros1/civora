"""Deterministische controle en nabewerking van LLM-extracties."""

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.schemas.opportunity_extraction import (
    OpportunityExtractionEnvelope,
)

POSTPROCESSING_VERSION = (
    "opportunity-postprocessing-v4"
)

REVIEW_ENFORCEMENT_ENABLED = False

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

    # Een niet-concrete maar correct onvertaalde startdatum.
    "startdatum is alleen vermeld als 'z.s.m.'",
    'startdatum is alleen vermeld als "z.s.m."',
    "startdatum is alleen vermeld als z.s.m.",
    "startdatum alleen vermeld als 'z.s.m.'",

    # Locatie die expliciet uit een werk-/kantoorlocatie volgt.
    "locatie is afgeleid uit vermelding gemeentehuis",
    "locatie afgeleid uit vermelding gemeentehuis",

    # Ontbrekende optionele tariefinformatie.
    "specifieke tariefinformatie ontbreekt",
    "tariefinformatie ontbreekt",
    "geen tariefinformatie",

    # Uitleg van correct afgeleide contractvorm.
    "employment_relationship afgeleid uit",
    "employment relationship afgeleid uit",
    "afgeleid uit contractinformatie",
    "broker/contractmodellen",

    # Contractvorm die deterministisch wordt gevalideerd/gecorrigeerd.
    "employment_relationship op 'both' gekozen",
    'employment_relationship op "both" gekozen',
    "employment relationship op 'both' gekozen",
    'employment relationship op "both" gekozen',
    "zelfstandige inzet lijkt toegestaan",
    "voorwaarden rond inleen en vog",

    # Publication date is optioneel.
    "publication_date niet expliciet vermeld",
    "publication date niet expliciet vermeld",
    "publicatiedatum niet expliciet vermeld",
    "publicatiedatum ontbreekt",

        # Unknown contractvorm is correct wanneer de bron
    # geen expliciete toegestane contractvorm noemt.
    "employment_relationship niet expliciet genoemd",
    "employment relationship niet expliciet genoemd",
    "contractvorm niet expliciet genoemd",

    # Meerdere expliciete werklocaties kunnen in één
    # location-veld gecombineerd worden.
    "location gecombineerd uit meerdere teksten",
    "locatie gecombineerd uit meerdere teksten",
    "exact standplaats niet eenduidig als enkelvoudig veld",


)

NON_ACTIONABLE_REVIEW_PATTERNS = (

    re.compile(
        r"startdatum.*z\.?\s*s\.?\s*m\.?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(geen|ontbrekende?).*tarief",
        re.IGNORECASE,
    ),
    re.compile(
        r"employment[_ ]relationship.*"
        r"niet\s+expliciet.*"
        r"(genoemd|vermeld)",
        re.IGNORECASE,
    ),

    re.compile(
        r"work[_ ]arrangement.*"
        r"niet\s+expliciet.*"
        r"(genoemd|vermeld)",
        re.IGNORECASE,
    ),

    re.compile(
        r"\blocation\b.*"
        r"\bniet\s+ingevuld\b.*"
        r"\b(?:provincie|regio)\b.*"
        r"\bgeen\s+concrete\b",
        re.IGNORECASE,
    ),
)

ZZP_ALLOWED_PATTERNS = (
    re.compile(
        r"\bmodel\s*4\b.{0,160}\bzzp",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bin\s+geval\s+u\s+een\s+zzp",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bzzp['’]?er\s+bent\b",
        re.IGNORECASE,
    ),
)


SECONDMENT_ALLOWED_PATTERNS = (
    re.compile(
        r"\bmodel\s*6\b.{0,200}\bdetach",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\btijdelijke\s+medewerker\s+detacheert\b",
        re.IGNORECASE,
    ),
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
    """Herken niet-actionabele reviewredenen."""

    normalized_reason = (
        reason.casefold()
    )

    is_non_actionable_term = any(
        term in normalized_reason
        for term in NON_ACTIONABLE_REVIEW_TERMS
    )

    is_non_actionable_pattern = any(
        pattern.search(reason)
        is not None
        for pattern
        in NON_ACTIONABLE_REVIEW_PATTERNS
    )

    return (
        is_non_actionable_term
        or is_non_actionable_pattern
    )



def _relationship_options_from_text(
    prepared_text: str,
) -> tuple[
    bool,
    bool,
]:
    """
    Detecteer expliciet toegestane ZZP- en
    detacheringsconstructies.
    """

    zzp_allowed = any(
        pattern.search(
            prepared_text
        )
        is not None
        for pattern in ZZP_ALLOWED_PATTERNS
    )

    secondment_allowed = any(
        pattern.search(
            prepared_text
        )
        is not None
        for pattern
        in SECONDMENT_ALLOWED_PATTERNS
    )

    return (
        zzp_allowed,
        secondment_allowed,
    )

def _extract_hours_per_week(
    prepared_text: str,
) -> tuple[float, float] | None:
    """
    Lees het gestructureerde Flextender-veld
    'Uren per week' uit de voorbereide tekst.
    """

    range_match = re.search(
        (
            r"(?im)"
            r"^[ \t]*uren[ \t]+per[ \t]+week[ \t]*\r?\n"
            r"[ \t]*(?:gemiddeld[ \t]+)?"
            r"(\d+(?:[.,]\d+)?)"
            r"[ \t]*(?:tot|t/m|[-–—])[ \t]*"
            r"(\d+(?:[.,]\d+)?)"
            r"[ \t]*$"
        ),
        prepared_text,
    )

    if range_match is not None:
        minimum = float(
            range_match.group(1).replace(
                ",",
                ".",
            )
        )

        maximum = float(
            range_match.group(2).replace(
                ",",
                ".",
            )
        )

        return (
            minimum,
            maximum,
        )

    single_match = re.search(
        (
            r"(?im)"
            r"^[ \t]*uren[ \t]+per[ \t]+week[ \t]*\r?\n"
            r"[ \t]*(?:gemiddeld[ \t]+)?"
            r"(\d+(?:[.,]\d+)?)"
            r"[ \t]*$"
        ),
        prepared_text,
    )

    if single_match is not None:
        hours = float(
            single_match.group(1).replace(
                ",",
                ".",
            )
        )

        return (
            hours,
            hours,
        )

    return None


def _has_explicit_on_site_evidence(
    prepared_text: str,
) -> bool:
    """
    Controleer of de bron expliciet aangeeft
    dat de werkzaamheden op locatie moeten
    worden uitgevoerd.
    """

    patterns = (
        re.compile(
            r"\bvolledig\s+op\s+locatie\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\buitsluitend\s+op\s+locatie\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bwerkzaamheden\s+worden\s+"
            r"(?:volledig|uitsluitend)\s+"
            r"op\s+locatie\s+uitgevoerd\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bthuiswerken\s+(?:is\s+)?"
            r"(?:niet\s+mogelijk|niet\s+toegestaan)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bgeen\s+mogelijkheid\s+"
            r"(?:tot|voor)\s+thuiswerken\b",
            re.IGNORECASE,
        ),
    )

    return any(
        pattern.search(
            prepared_text
        )
        is not None
        for pattern in patterns
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

    source_hours = _extract_hours_per_week(
        prepared_text
    )

    if source_hours is not None:
        (
            source_hours_min,
            source_hours_max,
        ) = source_hours

        if (
            opportunity.hours_per_week_min
            != source_hours_min
            or opportunity.hours_per_week_max
            != source_hours_max
        ):
            opportunity_updates[
                "hours_per_week_min"
            ] = source_hours_min

            opportunity_updates[
                "hours_per_week_max"
            ] = source_hours_max

            corrections.append(
                "Uren per week gecorrigeerd naar "
                f"{source_hours_min:g} - "
                f"{source_hours_max:g} op basis "
                "van het gestructureerde bronveld."
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
        opportunity.work_arrangement
        == "on_site"
        and not _has_explicit_on_site_evidence(
            prepared_text
        )
    ):
        opportunity_updates[
            "work_arrangement"
        ] = "unknown"

        corrections.append(
            "Werkvorm gecorrigeerd van on_site "
            "naar unknown omdat de bron geen "
            "expliciete verplichte fysieke "
            "werkvorm vermeldt."
        )

    if (
        opportunity.location
        and opportunity.province
        and opportunity.location.strip().casefold()
        == opportunity.province.strip().casefold()
    ):
        opportunity_updates[
            "location"
        ] = None

        corrections.append(
            "Locatie verwijderd omdat deze gelijk "
            "was aan de provincie/regio en geen "
            "concrete plaats of werklocatie "
            "vertegenwoordigde."
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
        opportunity.rate_min is None
        and opportunity.rate_max is None
        and opportunity.rate_period
        != "unknown"
    ):
        opportunity_updates[
            "rate_period"
        ] = "unknown"

        corrections.append(
            "Tariefperiode teruggezet naar unknown "
            "omdat geen minimum- of maximumtarief "
            "in de bron is vastgesteld."
        )

    (
        zzp_allowed,
        secondment_allowed,
    ) = _relationship_options_from_text(
        prepared_text
    )

    if (
        zzp_allowed
        and secondment_allowed
    ):
        if (
            opportunity.employment_relationship
            != "both"
        ):
            opportunity_updates[
                "employment_relationship"
            ] = "both"

            corrections.append(
                "Contractvorm gecorrigeerd naar both "
                "omdat de bron zowel ZZP als "
                "detachering expliciet toestaat."
            )

    elif (
        opportunity.employment_relationship
        == "both"
    ):
        if zzp_allowed:
            corrected_relationship = "zzp"

        elif secondment_allowed:
            corrected_relationship = "secondment"

        else:
            corrected_relationship = "unknown"

        opportunity_updates[
            "employment_relationship"
        ] = corrected_relationship

        corrections.append(
            "Contractvorm gecorrigeerd van both naar "
            f"{corrected_relationship} omdat niet beide "
            "contractvormen expliciet door de bron "
            "worden ondersteund."
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
        review_required=(
            bool(combined_review_reasons)
            if REVIEW_ENFORCEMENT_ENABLED
            else False
        ),
        corrections=tuple(
            corrections
        ),
    )