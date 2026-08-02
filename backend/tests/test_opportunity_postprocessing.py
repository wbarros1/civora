"""Tests voor deterministische extractienabewerking."""

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.schemas.opportunity_extraction import (
    ContactInformation,
    ExtractedOpportunity,
    OpportunityExtractionEnvelope,
)
from backend.app.services.opportunity_postprocessing import (
    post_process_extraction,
)


def test_normalizes_title_and_removes_unsupported_phone() -> None:
    """Titel en contactgegevens worden tegen de bron gecontroleerd."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title=(
                "Azure Netwerk Engineer - Kadaster"
            ),
            client_name="Kadaster",
            application_deadline=datetime(
                2026,
                7,
                22,
                8,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
            hours_per_week_min=40,
            hours_per_week_max=40,
            rate_min=125,
            rate_max=125,
            rate_period="hour",
            contact_information=(
                ContactInformation(
                    name="Louk Kirch",
                    email=(
                        "talentenregio@"
                        "flextender.nl"
                    ),
                    phone="+31 35 751 0777",
                )
            ),
        ),
        overall_confidence=0.82,
        review_reasons=[
            "Number of positions not stated",
            "Publication date not explicitly given",
            (
                "Duration_months not explicitly "
                "specified"
            ),
        ],
    )

    prepared_text = """
    Azure Netwerk Engineer - Kadaster
    Vragen over deze opdracht?
    Louk Kirch
    talentenregio@flextender.nl
    Opdracht
    Azure Netwerk Engineer
    Kadaster
    Een maximum uurtarief van € 125,00 exclusief btw.
    """

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=prepared_text,
        title_hint=(
            "Azure Netwerk Engineer"
        ),
        source_status="active",
        current_time=datetime(
            2026,
            7,
            30,
            8,
            0,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    opportunity = (
        result.extraction.opportunity
    )
    
    assert opportunity.rate_min is None
    assert opportunity.rate_max == 125

    assert (
        result.application_status
        == "expired"
    )

    assert result.review_required is False
    assert (
        result.extraction.review_reasons
        == []
    )

    assert len(result.corrections) == 3


def test_preserves_actionable_review_reason() -> None:
    """Een inhoudelijke tegenstrijdigheid blijft review vereisen."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Projectleider",
            client_name="Gemeente Voorbeeld",
            application_deadline=datetime(
                2026,
                9,
                1,
                12,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
            hours_per_week_min=32,
            hours_per_week_max=32,
        ),
        overall_confidence=0.82,
        review_reasons=[
            (
                "De contractvorm is in de bron "
                "tegenstrijdig beschreven."
            ),
        ],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=(
            "Projectleider\n"
            "Gemeente Voorbeeld\n"
            "32 uur per week"
        ),
        title_hint="Projectleider",
        source_status="active",
        current_time=datetime(
            2026,
            8,
            1,
            8,
            0,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    assert result.review_required is True

    assert result.extraction.review_reasons == [
        (
            "De contractvorm is in de bron "
            "tegenstrijdig beschreven."
        )
    ]

def test_filters_explanatory_review_reasons() -> None:
    """Uitleg van correcte veldkeuzes vereist geen review."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Azure Netwerk Engineer",
            client_name="Kadaster",
            application_deadline=datetime(
                2026,
                7,
                22,
                8,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
            hours_per_week_min=40,
            hours_per_week_max=40,
            rate_min=None,
            rate_max=125,
            rate_period="hour",
            employment_relationship=(
                "secondment"
            ),
        ),
        overall_confidence=0.85,
        review_reasons=[
            (
                "Tarief vermeld als maximaal "
                "€125; geen expliciet "
                "minimumtarief gegeven"
            ),
            (
                "Employment_relationship gezet "
                "op 'secondment' omdat "
                "detacherings- en "
                "arbeidsovereenkomst als "
                "verplicht worden genoemd"
            ),
        ],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=(
            "Azure Netwerk Engineer\n"
            "Kadaster\n"
            "Een maximum uurtarief van "
            "€ 125,00 exclusief btw.\n"
            "Dit is een detacheringsopdracht "
            "met een verplichte "
            "arbeidsovereenkomst."
        ),
        title_hint=(
            "Azure Netwerk Engineer"
        ),
        source_status="active",
        current_time=datetime(
            2026,
            7,
            30,
            9,
            0,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    assert (
        result.extraction.review_reasons
        == []
    )

    assert result.review_required is False

def test_filters_contract_and_start_date_explanations() -> None:
    """Correcte interpretaties en algemene voorbehouden vereisen geen review."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Azure Netwerk Engineer",
            client_name="Kadaster",
            start_date=datetime(
                2026,
                9,
                15,
            ).date(),
            application_deadline=datetime(
                2026,
                7,
                22,
                8,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
            hours_per_week_min=40,
            hours_per_week_max=40,
            rate_min=None,
            rate_max=125,
            rate_period="hour",
            employment_relationship=(
                "secondment"
            ),
        ),
        overall_confidence=0.85,
        review_reasons=[
            (
                "Employment_relationship op basis van "
                "vereiste driepartijen detachering en "
                "arbeidsovereenkomst geïnterpreteerd "
                "als 'secondment'."
            ),
            (
                "Startdatum vermeld 'onder voorbehoud' "
                "van offerteprocedure maar concrete datum "
                "is opgenomen; mogelijke verschuiving "
                "niet verder gespecificeerd."
            ),
        ],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=(
            "Azure Netwerk Engineer\n"
            "Kadaster\n"
            "Start 15-09-2026\n"
            "De startdatum is onder voorbehoud van "
            "tijdige afronding van de offerteprocedure.\n"
            "Dit is een detacheringsopdracht met een "
            "verplichte arbeidsovereenkomst."
        ),
        title_hint="Azure Netwerk Engineer",
        source_status="active",
        current_time=datetime(
            2026,
            7,
            30,
            9,
            0,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    assert result.review_required is False
    assert result.extraction.review_reasons == []
    assert (
        result.extraction
        .opportunity
        .employment_relationship
        == "secondment"
    )

def test_filters_contract_choice_and_missing_positions() -> None:
    """Correcte categorisatie en ontbrekende optionele velden vereisen geen review."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Azure Netwerk Engineer",
            client_name="Kadaster",
            application_deadline=datetime(
                2026,
                7,
                22,
                8,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
            hours_per_week_min=40,
            hours_per_week_max=40,
            employment_relationship=(
                "secondment"
            ),
        ),
        overall_confidence=0.80,
        review_reasons=[
            (
                "Employment_relationship gekozen als "
                "'secondment' omdat detacherings- en "
                "driepartijenovereenkomst verplicht zijn."
            ),
            (
                "Number_of_positions ontbreekt in bron."
            ),
        ],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=(
            "Azure Netwerk Engineer\n"
            "Kadaster\n"
            "40 uur per week\n"
            "Dit is een detacheringsopdracht met "
            "een verplichte driepartijenovereenkomst."
        ),
        title_hint="Azure Netwerk Engineer",
        source_status="active",
        current_time=datetime(
            2026,
            7,
            30,
            16,
            0,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    assert result.review_required is False
    assert result.extraction.review_reasons == []

    assert (
        result.extraction
        .opportunity
        .employment_relationship
        == "secondment"
    )