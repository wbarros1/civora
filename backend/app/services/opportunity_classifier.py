"""LLM-classificatie van Civora-opdrachten."""

from dataclasses import dataclass

from openai import OpenAI

from backend.app.core.config import (
    get_settings,
)
from backend.app.schemas.opportunity_classification import (
    OpportunityClassificationEnvelope,
)
from backend.app.services.opportunity_classification_input import (
    OpportunityClassificationInput,
    render_classification_input,
)


CLASSIFIER_VERSION = (
    "civora-vakgroep-v2"
)


DEVELOPER_PROMPT = """
Je classificeert Nederlandse publieke inhuuropdrachten voor Civora.

Beoordeel iedere opdracht onafhankelijk op relevantie voor precies
vier vakgroepen:

1. procesmanagement
2. data_ai
3. ict
4. finance

Je geeft voor ALLE vier vakgroepen een relevance_score van 0 tot 100
en een korte feitelijke reden.

Belangrijk:
- Kies zelf geen primaire vakgroep.
- Gebruik geen categorie 'overige'.
- Bepaal niet zelf welke scores als match tellen.
- Civora bepaalt primary, drempelwaarden en matches later
  deterministisch in Python.
- Meerdere vakgroepen mogen tegelijk hoog scoren.
- Verlaag een score niet alleen omdat een andere vakgroep nog beter
  past.
- Beoordeel de daadwerkelijke werkzaamheden, verantwoordelijkheden,
  eisen, wensen, competenties en skills.
- Baseer de classificatie uitsluitend op de aangeleverde informatie.
- Verzin geen werkzaamheden of expertise.

Vakgroepdefinities:

PROCESMANAGEMENT
Projectmanagement, programmamanagement, projectleiding,
procesmanagement, PMO, verander- en implementatiemanagement,
transformatie, organisatieontwikkeling, procesverbetering,
agile/scrum-begeleiding en vergelijkbare regie- of
veranderverantwoordelijkheden.

DATA & AI
Data engineering, data-analyse, business intelligence,
data science, artificial intelligence, machine learning,
data-architectuur, data governance, dataplatformen,
analytics en vergelijkbare data-intensieve werkzaamheden.

ICT
Softwareontwikkeling, applicaties, cloud, infrastructuur,
DevOps, cybersecurity, netwerken, technisch/functioneel beheer,
integraties, systeemarchitectuur en vergelijkbare
ICT-werkzaamheden.

FINANCE
Financial control, business control, accounting,
financieel advies, audit, treasury, financiële administratie,
financiële analyse en vergelijkbare financiële werkzaamheden.

Scoreinterpretatie:
0-39:
Geen of slechts zeer beperkte inhoudelijke relatie.

40-59:
Indirecte of ondersteunende relatie, maar niet substantieel genoeg
om de opdracht voor die vakgroep te positioneren.

60-74:
Duidelijk relevante werkzaamheden of expertise.

75-89:
Sterke inhoudelijke aansluiting.

90-100:
De vakgroep vormt een kernonderdeel van de opdracht.

Classificatieregels:
- Kijk verder dan alleen de functietitel.
- Organisatiecontext alleen is onvoldoende voor een hoge score.
- Een projectmanager binnen een IT-programma kan zowel hoog scoren
  op procesmanagement als substantieel op ICT.
- Een projectmanager voor een dataplatform kan relevant zijn voor
  procesmanagement, data_ai en ICT.
- Een technische rol bij een financiële organisatie is niet
  automatisch finance.
- Een datafunctie bij een gemeente blijft primair inhoudelijk
  een datafunctie.
- Een rol krijgt alleen een hoge score wanneer de werkzaamheden,
  verantwoordelijkheden, gevraagde ervaring of expertise daar
  daadwerkelijk aanleiding toe geven.

PROCESMANAGEMENT - aanvullende afbakening:
- Geef procesmanagement alleen een score van 60 of hoger wanneer
  het managen, ontwerpen, verbeteren, veranderen of regisseren van
  projecten, programma's, organisatieprocessen of implementaties
  een substantieel onderdeel van de opdracht vormt.
- Het uitvoeren van een bestaand werkproces is op zichzelf geen
  procesmanagement.
- Casemanagement, dossierbehandeling, intakegesprekken,
  klantbegeleiding, aanvragen afhandelen, eigen werk plannen,
  samenwerken met collega's of reguliere afstemming zijn op
  zichzelf onvoldoende voor een procesmanagement-score van 60
  of hoger.
- Operationele coördinatie telt alleen zwaar mee wanneer de
  professional aantoonbaar verantwoordelijkheid draagt voor
  bredere procesregie, verandering, implementatie of
  project-/programmasturing.

Confidence:
Geef één classification_confidence van 0 tot 1 voor de kwaliteit en
duidelijkheid van de totale classificatie.

Gebruik een lagere confidence wanneer:
- de opdrachtbeschrijving erg beperkt is;
- titel en inhoud elkaar tegenspreken;
- de inhoud uitzonderlijk breed of ambigu is;
- onvoldoende informatie beschikbaar is om vakgroepen goed te
  onderscheiden.

Review:
Gebruik review_reasons alleen voor echte classificatie-onzekerheid.
Schrijf reviewredenen in het Nederlands.
Gebruik maximaal vier korte reviewredenen.
Het feit dat meerdere vakgroepen relevant zijn is op zichzelf geen
reviewreden.
""".strip()


@dataclass(
    frozen=True,
    slots=True,
)
class OpportunityClassificationResult:
    """Classificatie plus technische OpenAI-metadata."""

    classification: (
        OpportunityClassificationEnvelope
    )

    response_id: str
    model_name: str
    classifier_version: str

    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


def classify_opportunity_with_llm(
    classification_input: OpportunityClassificationInput,
) -> OpportunityClassificationResult:
    """Classificeer één structured opportunity."""

    prepared_input = (
        render_classification_input(
            classification_input
        )
    )

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY ontbreekt."
        )

    with OpenAI(
        api_key=(
            settings.openai_api_key
            .get_secret_value()
        ),
    ) as client:
        response = client.responses.parse(
            model=(
                settings
                .openai_classification_model
            ),
            input=[
                {
                    "role": "developer",
                    "content": (
                        DEVELOPER_PROMPT
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Classificeer onderstaande "
                        "Civora-opdracht.\n\n"
                        "BEGIN OPDRACHT\n"
                        f"{prepared_input}\n"
                        "EINDE OPDRACHT"
                    ),
                },
            ],
            text_format=(
                OpportunityClassificationEnvelope
            ),
            reasoning={
                "effort": "minimal",
            },
            max_output_tokens=1_500,
            store=False,
        )

    if response.status != "completed":
        raise RuntimeError(
            "De OpenAI-classificatie "
            "is niet voltooid. "
            f"Status: {response.status}"
        )

    parsed_output = (
        response.output_parsed
    )

    if parsed_output is None:
        raise RuntimeError(
            "De OpenAI-response bevatte "
            "geen geparseerde classificatie."
        )

    usage = response.usage

    return OpportunityClassificationResult(
        classification=(
            parsed_output
        ),
        response_id=response.id,
        model_name=response.model,
        classifier_version=(
            CLASSIFIER_VERSION
        ),
        input_tokens=(
            usage.input_tokens
            if usage is not None
            else None
        ),
        output_tokens=(
            usage.output_tokens
            if usage is not None
            else None
        ),
        total_tokens=(
            usage.total_tokens
            if usage is not None
            else None
        ),
    )