"""Tests voor deterministische extractienabewerking."""

from datetime import date, datetime
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

def test_corrects_no_rate_and_both_contract_forms() -> None:
    """Geen tarief en meerdere contractvormen worden correct genormaliseerd."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Juridisch adviseur VTH",
            client_name="Gemeente Veere",
            location="Domburg (gemeentehuis)",
            province="Zeeland",
            work_arrangement="hybrid",
            start_date=None,
            duration_months=6,
            extension_possible=True,
            hours_per_week_min=32,
            hours_per_week_max=32,
            rate_min=None,
            rate_max=None,
            rate_period="hour",
            employment_relationship="zzp",
            application_deadline=datetime(
                2026,
                8,
                13,
                9,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
        ),
        overall_confidence=0.90,
        review_reasons=[
            (
                "Startdatum is alleen vermeld als "
                "'Z.s.m.' en kon niet exact worden "
                "vastgesteld, daarom niet ingevuld."
            ),
            (
                "Locatie is afgeleid uit vermelding "
                "gemeentehuis Domburg en regio Zeeland "
                "maar niet expliciet als plaats vermeld "
                "in adresvelden."
            ),
        ],
    )

    prepared_text = """
    Juridisch adviseur VTH
    Gemeente Veere
    32 uur per week
    Start Z.s.m.

    Kandidaat is bereid om minimaal de helft
    van de werkweek op kantoor aanwezig te zijn.

    Model 4 in geval u een ZZP'er bent.
    Model 5 in geval u een Toeleverancier bent
    die een zzp'er aanbiedt.
    Model 6 in het geval u een Toeleverancier bent
    die de Tijdelijke medewerker detacheert.

    De werkzaamheden vinden plaats op het
    gemeentehuis Domburg.
    """

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=prepared_text,
        title_hint="Juridisch adviseur VTH",
        source_status="active",
        current_time=datetime(
            2026,
            8,
            11,
            13,
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
    assert opportunity.rate_max is None
    assert (
        opportunity.rate_period
        == "unknown"
    )

    assert (
        opportunity.employment_relationship
        == "both"
    )

    assert result.review_required is False
    assert result.extraction.review_reasons == []

def test_filters_missing_rate_and_relationship_explanation() -> None:
    """Ontbrekend tarief en correcte contractafleiding vereisen geen review."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Juridisch adviseur VTH",
            client_name="Gemeente Veere",
            work_arrangement="hybrid",
            hours_per_week_min=32,
            hours_per_week_max=32,
            duration_months=6,
            extension_possible=True,
            rate_min=None,
            rate_max=None,
            rate_period="unknown",
            employment_relationship="both",
            application_deadline=datetime(
                2026,
                8,
                13,
                9,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
        ),
        overall_confidence=0.85,
        review_reasons=[
            (
                "Specifieke tariefinformatie "
                "ontbreekt"
            ),
            (
                "Employment_relationship afgeleid "
                "uit contractinformatie met "
                "broker/contractmodellen"
            ),
        ],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=(
            "Juridisch adviseur VTH\n"
            "Gemeente Veere\n"
            "32 uur per week\n"
            "Model 4 in geval u een ZZP'er bent.\n"
            "Model 6 in het geval een tijdelijke "
            "medewerker wordt gedetacheerd."
        ),
        title_hint="Juridisch adviseur VTH",
        source_status="active",
        current_time=datetime(
            2026,
            8,
            11,
            13,
            30,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    assert result.review_required is False
    assert result.extraction.review_reasons == []

def test_downgrades_unsupported_both_relationship() -> None:
    """Both vereist expliciete ondersteuning voor beide contractvormen."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Programmamanager Winterswijk",
            client_name="Provincie Gelderland",
            province="Gelderland",
            work_arrangement="hybrid",
            start_date=date(
                2026,
                9,
                7,
            ),
            end_date=date(
                2027,
                8,
                31,
            ),
            hours_per_week_min=24,
            hours_per_week_max=24,
            rate_min=140,
            rate_max=175,
            rate_currency="EUR",
            rate_period="hour",
            employment_relationship="both",
            application_deadline=datetime(
                2026,
                8,
                17,
                9,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
        ),
        overall_confidence=0.8,
        review_reasons=[
            (
                "Employment_relationship op 'both' "
                "gekozen omdat zowel zelfstandige "
                "inzet lijkt toegestaan maar ook "
                "voorwaarden rond inleen en VOG "
                "aanwezig zijn."
            ),
            (
                "publication_date niet expliciet "
                "vermeld in de bron."
            ),
        ],
    )

    prepared_text = """
    Programmamanager Winterswijk
    Provincie Gelderland

    De programmamanager werkt zelfstandig en
    zonder hiërarchische aansturing.

    Vrijheid in de werkvorm, locatie en planning.

    De functie is ingedeeld in functieschaal 14.
    De CAO is van toepassing inzake de
    inlenersbeloning.

    Voor uitvoering is een VOG vereist.
    """

    result = post_process_extraction(
        extraction=extraction,
        prepared_text=prepared_text,
        title_hint=(
            "Programmamanager Winterswijk"
        ),
        source_status="active",
        current_time=datetime(
            2026,
            8,
            11,
            13,
            30,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    opportunity = (
        result.extraction.opportunity
    )

    assert (
        opportunity.employment_relationship
        == "unknown"
    )

    assert result.review_required is False
    assert (
        result.extraction.review_reasons
        == []
    )

def test_filters_valid_unknown_relationship_and_combined_location() -> None:
    """Correcte onbekende contractvorm en gecombineerde locatie vragen geen review."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Programmamanager Winterswijk",
            client_name="Provincie Gelderland",
            location=(
                "Winterswijk / "
                "Provinciehuis Arnhem (1 dag/week)"
            ),
            province="Gelderland",
            work_arrangement="hybrid",
            start_date=date(
                2026,
                9,
                7,
            ),
            end_date=date(
                2027,
                8,
                31,
            ),
            hours_per_week_min=24,
            hours_per_week_max=24,
            rate_min=140,
            rate_max=175,
            rate_currency="EUR",
            rate_period="hour",
            employment_relationship="unknown",
            application_deadline=datetime(
                2026,
                8,
                17,
                9,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
        ),
        overall_confidence=0.8,
        review_reasons=[
            (
                "location gecombineerd uit meerdere "
                "teksten (Winterswijk en 1 dag/week "
                "Arnhem) maar exact standplaats niet "
                "eenduidig als enkelvoudig veld"
            ),
            (
                "employment_relationship niet "
                "expliciet genoemd in bron"
            ),
        ],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text="""
        Programmamanager Winterswijk
        Provincie Gelderland

        Hybride werken is mogelijk.
        Je werkt 1 dag per week op het
        Provinciehuis te Arnhem,
        1 dag per week in de regio
        en verder is thuiswerken mogelijk.
        """,
        title_hint="Programmamanager Winterswijk",
        source_status="active",
        current_time=datetime(
            2026,
            8,
            11,
            14,
            0,
            tzinfo=ZoneInfo(
                "Europe/Amsterdam"
            ),
        ),
    )

    assert (
        result.extraction.opportunity
        .employment_relationship
        == "unknown"
    )

    assert result.review_required is False
    assert result.extraction.review_reasons == []

def test_corrects_hours_per_week_range_from_source() -> None:
    """Een expliciete urenrange uit de bron corrigeert de LLM-output."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title=(
                "Senior Projectleider "
                "Mobiliteitshub"
            ),
            client_name="Gemeente Zwolle",
            province="Overijssel",
            work_arrangement="hybrid",
            hours_per_week_min=24,
            hours_per_week_max=24,
            duration_months=24,
            extension_possible=True,
            rate_min=None,
            rate_max=None,
            rate_period="unknown",
            employment_relationship="unknown",
        ),
        overall_confidence=0.84,
        review_reasons=[],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text="""
        Senior Projectleider Mobiliteitshub
        Gemeente Zwolle

        Uren per week
        24 tot 32

        Start
        Z.s.m.

        Is hybride werken mogelijk: Ja
        """,
        title_hint=(
            "Senior Projectleider "
            "Mobiliteitshub"
        ),
        source_status="active",
    )

    opportunity = (
        result.extraction.opportunity
    )

    assert (
        opportunity.hours_per_week_min
        == 24
    )

    assert (
        opportunity.hours_per_week_max
        == 32
    )

def test_extracts_single_hours_per_week_from_source() -> None:
    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Juridisch adviseur VTH",
            hours_per_week_min=None,
            hours_per_week_max=None,
        ),
        overall_confidence=0.9,
        review_reasons=[],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text="""
        Juridisch adviseur VTH

        Uren per week
        32
        """,
        title_hint="Juridisch adviseur VTH",
        source_status="active",
    )

    opportunity = (
        result.extraction.opportunity
    )

    assert opportunity.hours_per_week_min == 32
    assert opportunity.hours_per_week_max == 32


def test_extracts_average_hours_per_week_from_source() -> None:
    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Programmamanager Winterswijk",
            hours_per_week_min=None,
            hours_per_week_max=None,
        ),
        overall_confidence=0.9,
        review_reasons=[],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text="""
        Programmamanager Winterswijk

        Uren per week
        gemiddeld 24
        """,
        title_hint="Programmamanager Winterswijk",
        source_status="active",
    )

    opportunity = (
        result.extraction.opportunity
    )

    assert opportunity.hours_per_week_min == 24
    assert opportunity.hours_per_week_max == 24

def test_removes_unsupported_on_site_and_region_location() -> None:
    """Regio alleen bewijst geen locatie of on-site werkvorm."""

    extraction = OpportunityExtractionEnvelope(
        opportunity=ExtractedOpportunity(
            title="Business Analist DSO-LV",
            client_name="Kadaster",
            location="Gelderland",
            province="Gelderland",
            work_arrangement="on_site",
            start_date=date(
                2026,
                9,
                14,
            ),
            end_date=date(
                2027,
                8,
                31,
            ),
            hours_per_week_min=32,
            hours_per_week_max=36,
            rate_min=None,
            rate_max=118,
            rate_currency="EUR",
            rate_period="hour",
            employment_relationship="secondment",
            application_deadline=datetime(
                2026,
                8,
                24,
                8,
                0,
                tzinfo=ZoneInfo(
                    "Europe/Amsterdam"
                ),
            ),
        ),
        overall_confidence=0.88,
        review_reasons=[],
    )

    result = post_process_extraction(
        extraction=extraction,
        prepared_text="""
        Business Analist DSO-LV
        Kadaster

        Regio
        Gelderland

        LET OP!! Dit is een detacheringsopdracht
        met een driepartijenovereenkomst.

        Uren per week
        32-36

        Start
        14-09-2026

        Verloopt op
        maandag 24 augustus 2026

        Tijd & agenda
        08:00 uur
        """,
        title_hint=(
            "Business Analist DSO-LV"
        ),
        source_status="active",
    )

    opportunity = (
        result.extraction.opportunity
    )

    assert (
        opportunity.work_arrangement
        == "unknown"
    )

    assert opportunity.location is None

    assert (
        opportunity.province
        == "Gelderland"
    )

    assert result.review_required is False