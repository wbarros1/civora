"""LLM-extractie van publieke inhuuropdrachten."""

from dataclasses import dataclass

from openai import OpenAI

from backend.app.core.config import (
    get_settings,
)
from backend.app.schemas.opportunity_extraction import (
    OpportunityExtractionEnvelope,
)


PROMPT_VERSION = (
    "flextender-extraction-v4"
)


DEVELOPER_PROMPT = """
Je extraheert gestructureerde gegevens uit Nederlandse publieke
inhuuropdrachten.

Gebruik uitsluitend informatie die letterlijk of ondubbelzinnig
uit de aangeleverde tekst volgt.

Algemene regels:
1. Verzin nooit ontbrekende informatie.
2. Gebruik null voor een ontbrekende enkelvoudige waarde.
3. Gebruik een lege lijst wanneer een lijst ontbreekt.
4. Houd alle teksten compact en feitelijk.
5. Gebruik ISO 8601 voor datums en datums met tijd.
6. Een Nederlandse deadline gebruikt de tijdzone Europe/Amsterdam.

Veldregels:
7. title bevat alleen de functietitel. Voeg opdrachtgever,
   plaats of regio niet aan de titel toe.
8. Beperk description tot maximaal 700 tekens.
9. Een concrete datum bij 'Duur' is end_date.
10. Vul duration_months alleen in wanneer de bron expliciet
    een aantal maanden noemt.
11. Zet één urenwaarde in zowel hours_per_week_min als
    hours_per_week_max.
12. Gebruik rate_period='hour' bij een uurtarief.
13. Wanneer alleen een maximumtarief staat vermeld, vul uitsluitend
    rate_max in en laat rate_min null.
14. Wanneer alleen een minimumtarief staat vermeld, vul uitsluitend
    rate_min in en laat rate_max null.
15. Vul rate_min en rate_max alleen met dezelfde waarde wanneer de
    bron expliciet één vast tarief noemt, zonder woorden zoals
    minimaal, maximaal, vanaf of tot.
14. Gebruik extension_possible=true wanneer verlenging wordt genoemd.
15. Gebruik employment_relationship='secondment' wanneer een
    arbeidsovereenkomst of detachering verplicht is en zzp niet
    zelfstandig is toegestaan.
16. Gebruik work_arrangement='hybrid' wanneer zowel thuiswerken
    als verplichte kantoordagen worden genoemd.

Lijsten:
17. requirements bevat uitsluitend harde eisen en knock-outcriteria.
18. wishes bevat uitsluitend gunningscriteria en voorkeuren.
19. Beperk requirements tot maximaal 15 compacte items.
20. Beperk wishes tot maximaal 8 compacte items.
21. Beperk competencies tot maximaal 12 items.
22. Beperk skills tot maximaal 15 items.
23. Elk lijstitem bevat maximaal één eis, wens, competentie of skill.
24. Vermijd dubbele of inhoudelijk overlappende lijstitems.

Contactgegevens:
25. Neem een naam, e-mailadres of telefoonnummer alleen over wanneer
    dit letterlijk in de tekst staat.
26. Leid nooit een telefoonnummer of e-mailadres af.
27. Koppel een telefoonnummer alleen aan de contactpersoon wanneer
    beide duidelijk samen in dezelfde contactsectie staan.

Confidence en review:
28. Geef één conservatieve overall_confidence.
29. Gebruik 1.0 alleen wanneer vrijwel alle kernvelden letterlijk
    en ondubbelzinnig aanwezig zijn.
30. Voeg alleen een review_reason toe wanneer de onduidelijkheid een
    kernveld beïnvloedt.
    31. Ontbrekende optionele velden zoals publication_date,
    number_of_positions en duration_months zijn geen reden voor review.
32. Schrijf alle reviewredenen in het Nederlands.
33. Voeg geen reviewreden toe wanneer een waarde simpelweg niet in
    de bron staat en het veld optioneel is.
34. Gebruik maximaal vier korte reviewredenen.
35. Gebruik review_reasons niet om correcte veldkeuzes uit te leggen.
36. Een ontbrekend minimumtarief bij een expliciet maximumtarief is
    geen reviewreden.
37. Het kiezen van employment_relationship op basis van duidelijke
    contractvoorwaarden is geen reviewreden.
38. Het correct afleiden van employment_relationship uit duidelijke
    contractvoorwaarden is geen reviewreden.
39. Een algemeen voorbehoud dat een concrete startdatum mogelijk nog
    kan verschuiven is geen reviewreden.
40. Voeg voor start_date alleen een reviewreden toe wanneer meerdere
    verschillende concrete startdatums worden genoemd of wanneer geen
    concrete startdatum kan worden vastgesteld.
""".strip()


@dataclass(
    frozen=True,
    slots=True,
)
class OpportunityExtractionResult:
    """Resultaat plus technische API-metadata."""

    extraction: OpportunityExtractionEnvelope
    response_id: str
    model_name: str
    prompt_version: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


def extract_opportunity_with_llm(
    prepared_text: str,
) -> OpportunityExtractionResult:
    """Extraheer één voorbewerkte opdracht met Structured Outputs."""

    if not prepared_text.strip():
        raise ValueError(
            "De voorbereide opdrachttekst mag niet leeg zijn."
        )

    settings = get_settings()

    with OpenAI(
        api_key=(
            settings.openai_api_key
            .get_secret_value()
        ),
    ) as client:
        response = client.responses.parse(
            model=(
                settings.openai_extraction_model
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
                        "Extraheer onderstaande "
                        "inhuuropdracht.\n\n"
                        "BEGIN OPDRACHT\n"
                        f"{prepared_text}\n"
                        "EINDE OPDRACHT"
                    ),
                },
            ],
            text_format=(
                OpportunityExtractionEnvelope
            ),
            reasoning={
                "effort": "minimal",
            },
            max_output_tokens=3_500,
            store=False,
        )

    if response.status != "completed":
        raise RuntimeError(
            "De OpenAI-response is niet voltooid. "
            f"Status: {response.status}"
        )

    parsed_output = (
        response.output_parsed
    )

    if parsed_output is None:
        raise RuntimeError(
            "De OpenAI-response bevatte geen "
            "geparseerde extractie."
        )

    usage = response.usage

    return OpportunityExtractionResult(
        extraction=parsed_output,
        response_id=response.id,
        model_name=response.model,
        prompt_version=PROMPT_VERSION,
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