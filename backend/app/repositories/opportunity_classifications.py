"""Databasefuncties voor Civora vakgroepclassificaties."""

from dataclasses import dataclass
from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)


CLASSIFICATION_COLUMNS = (
    "id,"
    "opportunity_extraction_run_id,"
    "structured_opportunity_id,"
    "primary_vakgroep,"
    "classification_confidence,"
    "classifier_version,"
    "classification_source,"
    "manual_override,"
    "relevance_threshold,"
    "max_matches,"
    "review_reasons,"
    "classified_at,"
    "created_at,"
    "updated_at"
)


CLASSIFICATION_INPUT_COLUMNS = (
    "id,"
    "source_reference,"
    "title,"
    "client_name,"
    "description,"
    "education_level,"
    "minimum_years_experience,"
    "requirements,"
    "wishes,"
    "competencies,"
    "skills"
)


@dataclass(
    frozen=True,
    slots=True,
)
class ClassificationContext:
    """Extraction-run plus structured opportunity."""

    extraction_run_id: str
    structured_opportunity_id: str
    source_reference: str
    opportunity: dict[str, Any]


def _first_dict(
    data: Any,
) -> dict[str, Any] | None:
    """Geef het eerste geldige dictionary-record terug."""

    if not isinstance(
        data,
        list,
    ):
        return None

    for row in data:
        if isinstance(
            row,
            dict,
        ):
            return row

    return None

def list_opportunities_for_classification(
    *,
    classifier_version: str,
    limit: int,
) -> list[str]:
    """
    Selecteer actieve opportunities waarvan de laatste succesvolle
    extractierun nog niet met deze classifier-versie is verwerkt.
    """

    if limit < 1:
        raise ValueError(
            "limit moet minimaal 1 zijn."
        )

    if not classifier_version.strip():
        raise ValueError(
            "classifier_version mag niet leeg zijn."
        )

    client = get_supabase_client()

    # ---------------------------------------------------------
    # 1. Actieve structured opportunities
    # ---------------------------------------------------------

    active_response = (
        client.table(
            "structured_opportunities"
        )
        .select(
            "id,"
            "source_reference,"
            "updated_at"
        )
        .eq(
            "source_status",
            "active",
        )
        .order(
            "updated_at",
            desc=True,
        )
        .limit(1000)
        .execute()
    )

    active_rows = [
        row
        for row in (
            active_response.data or []
        )
        if isinstance(
            row,
            dict,
        )
    ]

    if not active_rows:
        return []

    active_by_reference: dict[
        str,
        str,
    ] = {}

    ordered_references: list[str] = []

    for row in active_rows:
        reference = row.get(
            "source_reference"
        )

        structured_id = row.get(
            "id"
        )

        if not isinstance(
            reference,
            str,
        ):
            continue

        if not isinstance(
            structured_id,
            str,
        ):
            continue

        reference = (
            reference.strip()
        )

        structured_id = (
            structured_id.strip()
        )

        if not reference:
            continue

        if not structured_id:
            continue

        active_by_reference[
            reference
        ] = structured_id

        ordered_references.append(
            reference
        )

    if not ordered_references:
        return []

    # ---------------------------------------------------------
    # 2. Succesvolle extraction-runs ophalen
    # ---------------------------------------------------------

    runs_response = (
        client.table(
            "opportunity_extraction_runs"
        )
        .select(
            "id,"
            "source_reference,"
            "structured_opportunity_id,"
            "error_type,"
            "completed_at,"
            "created_at"
        )
        .in_(
            "source_reference",
            ordered_references,
        )
        .order(
            "created_at",
            desc=True,
        )
        .execute()
    )

    latest_runs: dict[
        str,
        str,
    ] = {}

    for row in (
        runs_response.data or []
    ):
        if not isinstance(
            row,
            dict,
        ):
            continue

        reference = row.get(
            "source_reference"
        )

        run_id = row.get(
            "id"
        )

        structured_id = row.get(
            "structured_opportunity_id"
        )

        if not isinstance(
            reference,
            str,
        ):
            continue

        if not isinstance(
            run_id,
            str,
        ):
            continue

        if not isinstance(
            structured_id,
            str,
        ):
            continue

        if reference in latest_runs:
            continue

        expected_structured_id = (
            active_by_reference.get(
                reference
            )
        )

        if (
            structured_id
            != expected_structured_id
        ):
            continue

        if row.get(
            "error_type"
        ) is not None:
            continue

        if row.get(
            "completed_at"
        ) is None:
            continue

        latest_runs[
            reference
        ] = run_id

    if not latest_runs:
        return []

    # ---------------------------------------------------------
    # 3. Bestaande classifications voor deze runs ophalen
    # ---------------------------------------------------------

    run_ids = list(
        latest_runs.values()
    )

    classifications_response = (
        client.table(
            "opportunity_classifications"
        )
        .select(
            "opportunity_extraction_run_id"
        )
        .eq(
            "classifier_version",
            classifier_version,
        )
        .in_(
            "opportunity_extraction_run_id",
            run_ids,
        )
        .execute()
    )

    classified_run_ids: set[str] = set()

    for row in (
        classifications_response.data or []
    ):
        if not isinstance(
            row,
            dict,
        ):
            continue

        run_id = row.get(
            "opportunity_extraction_run_id"
        )

        if isinstance(
            run_id,
            str,
        ):
            classified_run_ids.add(
                run_id
            )

    # ---------------------------------------------------------
    # 4. Alleen nog niet geclassificeerde opportunities
    # ---------------------------------------------------------

    selected: list[str] = []

    for reference in (
        ordered_references
    ):
        run_id = latest_runs.get(
            reference
        )

        if run_id is None:
            continue

        if (
            run_id
            in classified_run_ids
        ):
            continue

        selected.append(
            reference
        )

        if len(
            selected
        ) >= limit:
            break

    return selected

def get_latest_classification_context(
    source_reference: str,
) -> ClassificationContext:
    """Haal de laatste succesvolle extraction-run en opportunity op."""

    client = get_supabase_client()

    run_response = (
        client.table(
            "opportunity_extraction_runs"
        )
        .select(
            "id,"
            "structured_opportunity_id,"
            "source_reference,"
            "status,"
            "error_type,"
            "completed_at,"
            "created_at"
        )
        .eq(
            "source_reference",
            source_reference,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(20)
        .execute()
    )

    extraction_run: (
        dict[str, Any] | None
    ) = None

    for row in (
        run_response.data or []
    ):
        if not isinstance(
            row,
            dict,
        ):
            continue

        structured_id = row.get(
            "structured_opportunity_id"
        )

        if not isinstance(
            structured_id,
            str,
        ):
            continue

        if not structured_id.strip():
            continue

        if row.get(
            "error_type"
        ) is not None:
            continue

        if row.get(
            "completed_at"
        ) is None:
            continue

        extraction_run = row
        break

    if extraction_run is None:
        raise RuntimeError(
            "Geen succesvolle extractierun gevonden "
            f"voor referentie {source_reference}."
        )

    structured_opportunity_id = str(
        extraction_run[
            "structured_opportunity_id"
        ]
    )

    opportunity_response = (
        client.table(
            "structured_opportunities"
        )
        .select(
            CLASSIFICATION_INPUT_COLUMNS
        )
        .eq(
            "id",
            structured_opportunity_id,
        )
        .limit(1)
        .execute()
    )

    opportunity = _first_dict(
        opportunity_response.data
    )

    if opportunity is None:
        raise RuntimeError(
            "De structured opportunity van "
            "de extractierun is niet gevonden."
        )

    return ClassificationContext(
        extraction_run_id=str(
            extraction_run["id"]
        ),
        structured_opportunity_id=(
            structured_opportunity_id
        ),
        source_reference=str(
            extraction_run[
                "source_reference"
            ]
        ),
        opportunity=opportunity,
    )


def get_existing_classification(
    *,
    extraction_run_id: str,
    classifier_version: str,
) -> dict[str, Any] | None:
    """Zoek een bestaande classification voor run + versie."""

    client = get_supabase_client()

    response = (
        client.table(
            "opportunity_classifications"
        )
        .select(
            CLASSIFICATION_COLUMNS
        )
        .eq(
            "opportunity_extraction_run_id",
            extraction_run_id,
        )
        .eq(
            "classifier_version",
            classifier_version,
        )
        .limit(1)
        .execute()
    )

    classification = _first_dict(
        response.data
    )

    if classification is None:
        return None

    scores_response = (
        client.table(
            "opportunity_vakgroep_scores"
        )
        .select(
            "id,"
            "classification_id,"
            "vakgroep,"
            "relevance_score,"
            "reason"
        )
        .eq(
            "classification_id",
            classification["id"],
        )
        .execute()
    )

    classification[
        "scores"
    ] = [
        row
        for row in (
            scores_response.data or []
        )
        if isinstance(
            row,
            dict,
        )
    ]

    return classification


def persist_classification(
    *,
    extraction_run_id: str,
    structured_opportunity_id: str,
    primary_vakgroep: str,
    classification_confidence: float,
    classifier_version: str,
    relevance_threshold: int,
    max_matches: int,
    review_reasons: list[str],
    scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """Sla één classification plus vier scores op."""

    if len(scores) != 4:
        raise ValueError(
            "Een Civora-classificatie moet "
            "exact vier vakgroepscores bevatten."
        )

    vakgroepen = {
        str(
            score.get(
                "vakgroep"
            )
        )
        for score in scores
    }

    expected_vakgroepen = {
        "procesmanagement",
        "data_ai",
        "ict",
        "finance",
    }

    if (
        vakgroepen
        != expected_vakgroepen
    ):
        raise ValueError(
            "De classificatie moet exact scores "
            "bevatten voor procesmanagement, "
            "data_ai, ict en finance."
        )

    client = get_supabase_client()

    insert_response = (
        client.table(
            "opportunity_classifications"
        )
        .insert(
            {
                "opportunity_extraction_run_id": (
                    extraction_run_id
                ),
                "structured_opportunity_id": (
                    structured_opportunity_id
                ),
                "primary_vakgroep": (
                    primary_vakgroep
                ),
                "classification_confidence": (
                    classification_confidence
                ),
                "classifier_version": (
                    classifier_version
                ),
                "classification_source": "llm",
                "manual_override": False,
                "relevance_threshold": (
                    relevance_threshold
                ),
                "max_matches": (
                    max_matches
                ),
                "review_reasons": (
                    review_reasons
                ),
            }
        )
        .execute()
    )

    classification = _first_dict(
        insert_response.data
    )

    if classification is None:
        raise RuntimeError(
            "De opportunity-classificatie "
            "kon niet worden opgeslagen."
        )

    classification_id = str(
        classification["id"]
    )

    score_payloads = [
        {
            "classification_id": (
                classification_id
            ),
            "vakgroep": (
                score["vakgroep"]
            ),
            "relevance_score": (
                score[
                    "relevance_score"
                ]
            ),
            "reason": (
                score["reason"]
            ),
        }
        for score in scores
    ]

    try:
        score_response = (
            client.table(
                "opportunity_vakgroep_scores"
            )
            .insert(
                score_payloads
            )
            .execute()
        )

        stored_scores = [
            row
            for row in (
                score_response.data or []
            )
            if isinstance(
                row,
                dict,
            )
        ]

        if len(
            stored_scores
        ) != 4:
            raise RuntimeError(
                "Niet alle vier vakgroepscores "
                "zijn opgeslagen."
            )

    except Exception:
        # Voorkom een half opgeslagen classificatie.
        (
            client.table(
                "opportunity_classifications"
            )
            .delete()
            .eq(
                "id",
                classification_id,
            )
            .execute()
        )

        raise

    classification[
        "scores"
    ] = stored_scores

    return classification