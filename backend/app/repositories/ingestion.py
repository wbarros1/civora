"""Databasequeries voor bronophalingen en ruwe opdrachten."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.app.database.client import get_supabase_client
from backend.app.schemas.ingestion import (
    FetchRun,
    FetchRunStatus,
    FetchTrigger,
    RawFormat,
    RawOpportunity,
    RawUpsertResult,
    SourceOpportunityStatus,
)
from backend.app.services.content_hashing import (
    calculate_content_hash,
    calculate_normalized_content_hash,
)
from backend.app.services.source_lifecycle import (
    evaluate_missing_closure_safety,
)


def utc_now() -> datetime:
    """Geef de huidige datum en tijd in UTC terug."""

    return datetime.now(timezone.utc)

def create_fetch_run(
    *,
    source_id: UUID,
    triggered_by: FetchTrigger = "manual",
    request_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FetchRun:
    """Registreer het begin van een ophaalactie."""

    client = get_supabase_client()
    started_at = utc_now()

    payload = {
        "source_id": str(source_id),
        "status": "running",
        "triggered_by": triggered_by,
        "request_url": request_url,
        "started_at": started_at.isoformat(),
        "metadata": metadata or {},
    }

    response = (
        client
        .table("fetch_runs")
        .insert(payload)
        .select("*")
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "De fetch run kon niet worden aangemaakt."
        )

    return FetchRun.model_validate(response.data[0])

def finish_fetch_run(
    *,
    fetch_run_id: UUID,
    source_id: UUID,
    status: FetchRunStatus,
    items_discovered: int = 0,
    items_new: int = 0,
    items_changed: int = 0,
    items_unchanged: int = 0,
    items_failed: int = 0,
    http_status: int | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FetchRun:
    """Sluit een ophaalactie af en werk de bronstatus bij."""

    if status in {"queued", "running"}:
        raise ValueError(
            "Een afgeronde fetch run moet succeeded, partial of failed zijn."
        )

    client = get_supabase_client()
    finished_at = utc_now()

    run_payload = {
        "status": status,
        "finished_at": finished_at.isoformat(),
        "items_discovered": items_discovered,
        "items_new": items_new,
        "items_changed": items_changed,
        "items_unchanged": items_unchanged,
        "items_failed": items_failed,
        "http_status": http_status,
        "error_message": error_message,
        "metadata": metadata or {},
    }

    response = (
        client
        .table("fetch_runs")
        .update(run_payload)
        .eq("id", str(fetch_run_id))
        .select("*")
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"Fetch run '{fetch_run_id}' kon niet worden afgerond."
        )

    if status == "succeeded":
        source_payload = {
            "last_success_at": finished_at.isoformat(),
            "last_error_message": None,
        }
    else:
        source_payload = {
            "last_error_at": finished_at.isoformat(),
            "last_error_message": (
                error_message
                or f"Fetch run afgerond met status '{status}'."
            ),
        }

    (
        client
        .table("sources")
        .update(source_payload)
        .eq("id", str(source_id))
        .execute()
    )

    return FetchRun.model_validate(response.data[0])

def _get_latest_version_number(
    raw_opportunity_id: UUID,
) -> int:
    """Haal het hoogste bestaande versienummer op."""

    client = get_supabase_client()

    response = (
        client
        .table("raw_opportunity_versions")
        .select("version_number")
        .eq(
            "raw_opportunity_id",
            str(raw_opportunity_id),
        )
        .order(
            "version_number",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return 0

    return int(
        response.data[0]["version_number"]
    )

def _insert_raw_version(
    *,
    raw_opportunity_id: UUID,
    fetch_run_id: UUID,
    version_number: int,
    source_url: str,
    raw_format: RawFormat,
    raw_content: str,
    content_hash: str,
    normalized_content_hash: str,
    metadata: dict[str, Any],
) -> None:
    """Sla een onveranderlijke ruwe versie op."""

    client = get_supabase_client()

    payload = {
        "raw_opportunity_id": str(raw_opportunity_id),
        "fetch_run_id": str(fetch_run_id),
        "version_number": version_number,
        "source_url": source_url,
        "raw_format": raw_format,
        "raw_content": raw_content,
        "content_hash": content_hash,
        "normalized_content_hash": normalized_content_hash,
        "metadata": metadata,
    }

    (
        client
        .table("raw_opportunity_versions")
        .insert(payload)
        .execute()
    )

def store_raw_opportunity(
    *,
    source_id: UUID,
    fetch_run_id: UUID,
    source_reference: str,
    source_url: str,
    raw_content: str,
    raw_format: RawFormat,
    title_hint: str | None = None,
    published_at: datetime | None = None,
    source_status: SourceOpportunityStatus = "active",
    metadata: dict[str, Any] | None = None,
) -> RawUpsertResult:
    """
    Sla ruwe brondata op.

    Mogelijke resultaten:
    - created: nieuwe bronopdracht;
    - unchanged: bestaande inhoud is gelijk;
    - changed: bestaande inhoud is gewijzigd.
    """

    if not source_reference.strip():
        raise ValueError(
            "source_reference mag niet leeg zijn."
        )

    if not source_url.strip():
        raise ValueError(
            "source_url mag niet leeg zijn."
        )

    if not raw_content.strip():
        raise ValueError(
            "raw_content mag niet leeg zijn."
        )

    client = get_supabase_client()
    now = utc_now()
    content_hash = calculate_content_hash(
        raw_content
    )

    normalized_content_hash = (
        calculate_normalized_content_hash(
            content=raw_content,
            raw_format=raw_format,
        )
    )

    opportunity_metadata = metadata or {}

    existing_response = (
        client
        .table("raw_opportunities")
        .select("*")
        .eq("source_id", str(source_id))
        .eq("source_reference", source_reference)
        .limit(1)
        .execute()
    )

    existing_data = (
        existing_response.data[0]
        if existing_response.data
        else None
    )

    if existing_data is None:
        insert_payload = {
            "source_id": str(source_id),
            "source_reference": source_reference,
            "source_url": source_url,
            "title_hint": title_hint,
            "raw_format": raw_format,
            "raw_content": raw_content,
            "content_hash": content_hash,
            "normalized_content_hash": (
                normalized_content_hash
            ),
            "source_status": source_status,
            "processing_status": "pending",
            "latest_fetch_run_id": str(fetch_run_id),
            "published_at": (
                published_at.isoformat()
                if published_at
                else None
            ),
            "first_seen_at": now.isoformat(),
            "last_seen_at": now.isoformat(),
            "metadata": opportunity_metadata,
        }

        insert_response = (
            client
            .table("raw_opportunities")
            .insert(insert_payload)
            .select("*")
            .execute()
        )

        if not insert_response.data:
            raise RuntimeError(
                "De ruwe opdracht kon niet worden aangemaakt."
            )

        opportunity = RawOpportunity.model_validate(
            insert_response.data[0]
        )

        _insert_raw_version(
            raw_opportunity_id=opportunity.id,
            fetch_run_id=fetch_run_id,
            version_number=1,
            source_url=source_url,
            raw_format=raw_format,
            raw_content=raw_content,
            content_hash=content_hash,
            normalized_content_hash=(
                normalized_content_hash
            ),
            metadata=opportunity_metadata,
        )

        return RawUpsertResult(
            action="created",
            opportunity=opportunity,
            version_number=1,
        )

    existing_opportunity = RawOpportunity.model_validate(
        existing_data
    )

    latest_version_number = _get_latest_version_number(
        existing_opportunity.id
    )

    existing_normalized_content_hash = (
        existing_opportunity.normalized_content_hash
    )

    if existing_normalized_content_hash is None:
        existing_normalized_content_hash = (
            calculate_normalized_content_hash(
                content=existing_opportunity.raw_content,
                raw_format=existing_opportunity.raw_format,
            )
        )

    if (
        existing_normalized_content_hash
        == normalized_content_hash
    ):
        update_payload = {
            "source_url": source_url,
            "source_status": source_status,
            "raw_format": raw_format,
            "raw_content": raw_content,
            "content_hash": content_hash,
            "normalized_content_hash": (
                normalized_content_hash
            ),
            "last_seen_at": now.isoformat(),
            "latest_fetch_run_id": str(fetch_run_id),
            "metadata": opportunity_metadata,
        }

        if title_hint is not None:
            update_payload["title_hint"] = title_hint

        update_response = (
            client
            .table("raw_opportunities")
            .update(update_payload)
            .eq("id", str(existing_opportunity.id))
            .select("*")
            .execute()
        )

        if not update_response.data:
            raise RuntimeError(
                "De bestaande ruwe opdracht kon niet worden bijgewerkt."
            )

        return RawUpsertResult(
            action="unchanged",
            opportunity=RawOpportunity.model_validate(
                update_response.data[0]
            ),
            version_number=latest_version_number,
        )

    new_version_number = latest_version_number + 1

    _insert_raw_version(
        raw_opportunity_id=existing_opportunity.id,
        fetch_run_id=fetch_run_id,
        version_number=new_version_number,
        source_url=source_url,
        raw_format=raw_format,
        raw_content=raw_content,
        content_hash=content_hash,
        normalized_content_hash=(
            normalized_content_hash
        ),
        metadata=opportunity_metadata,
    )

    existing_published_at = (
        published_at
        if published_at is not None
        else existing_opportunity.published_at
    )

    changed_payload = {
        "source_url": source_url,
        "source_status": source_status,
        "title_hint": title_hint,
        "raw_format": raw_format,
        "raw_content": raw_content,
        "content_hash": content_hash,
        "normalized_content_hash": (
            normalized_content_hash
        ),
        "processing_status": "pending",
        "latest_fetch_run_id": str(fetch_run_id),
        "published_at": (
            existing_published_at.isoformat()
            if existing_published_at is not None
            else None
        ),
        "last_seen_at": now.isoformat(),
        "metadata": opportunity_metadata,
    }

    changed_response = (
        client
        .table("raw_opportunities")
        .update(changed_payload)
        .eq("id", str(existing_opportunity.id))
        .select("*")
        .execute()
    )

    if not changed_response.data:
        raise RuntimeError(
            "De gewijzigde ruwe opdracht kon niet worden bijgewerkt."
        )

    return RawUpsertResult(
        action="changed",
        opportunity=RawOpportunity.model_validate(
            changed_response.data[0]
        ),
        version_number=new_version_number,
    )

@dataclass(
    frozen=True,
    slots=True,
)
class MissingOpportunityClosureResult:
    """Resultaat van het sluiten van verdwenen opdrachten."""

    executed: bool
    closed_count: int
    closed_references: tuple[str, ...]
    current_discovered_count: int
    previous_discovered_count: int | None
    minimum_allowed_count: int | None
    skipped_reason: str | None

def _get_previous_successful_full_run_count(
    *,
    source_id: UUID,
) -> int | None:
    """Vind de laatste succesvolle volledige run."""

    client = get_supabase_client()

    response = (
        client.table("fetch_runs")
        .select(
            "id,items_discovered,metadata,created_at"
        )
        .eq(
            "source_id",
            str(source_id),
        )
        .eq(
            "status",
            "succeeded",
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(50)
        .execute()
    )

    rows = response.data or []

    for row in rows:
        if not isinstance(row, dict):
            continue

        metadata = row.get("metadata")

        if not isinstance(metadata, dict):
            continue

        if metadata.get("mode") != "full":
            continue

        items_discovered = row.get(
            "items_discovered"
        )

        if isinstance(
            items_discovered,
            int,
        ):
            return items_discovered

    return None


def _list_active_source_opportunities(
    *,
    source_id: UUID,
    page_size: int = 500,
) -> list[dict[str, Any]]:
    """Lees alle actieve opdrachten van één bron op."""

    client = get_supabase_client()

    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        response = (
            client.table("raw_opportunities")
            .select(
                "id,source_reference,source_status"
            )
            .eq(
                "source_id",
                str(source_id),
            )
            .eq(
                "source_status",
                "active",
            )
            .range(
                offset,
                offset + page_size - 1,
            )
            .execute()
        )

        page_rows = response.data or []

        rows.extend(
            row
            for row in page_rows
            if isinstance(row, dict)
        )

        if len(page_rows) < page_size:
            break

        offset += page_size

    return rows


def close_missing_raw_opportunities(
    *,
    source_id: UUID,
    fetch_run_id: UUID,
    discovered_references: set[str],
    minimum_discovered_count: int = 50,
    minimum_previous_ratio: float = 0.70,
    update_batch_size: int = 100,
) -> MissingOpportunityClosureResult:
    """
    Sluit actieve opdrachten die niet meer zijn ontdekt.

    De actie wordt alleen uitgevoerd wanneer de discovery voldoende
    groot is ten opzichte van de vorige succesvolle volledige run.
    """

    cleaned_references = {
        reference.strip()
        for reference in discovered_references
        if reference.strip().isdigit()
    }

    current_discovered_count = len(
        cleaned_references
    )

    previous_discovered_count = (
        _get_previous_successful_full_run_count(
            source_id=source_id
        )
    )

    safety_decision = (
        evaluate_missing_closure_safety(
            current_discovered_count=(
                current_discovered_count
            ),
            previous_discovered_count=(
                previous_discovered_count
            ),
            minimum_discovered_count=(
                minimum_discovered_count
            ),
            minimum_previous_ratio=(
                minimum_previous_ratio
            ),
        )
    )

    if not safety_decision.allowed:
        return MissingOpportunityClosureResult(
            executed=False,
            closed_count=0,
            closed_references=(),
            current_discovered_count=(
                current_discovered_count
            ),
            previous_discovered_count=(
                previous_discovered_count
            ),
            minimum_allowed_count=(
                safety_decision.minimum_allowed_count
            ),
            skipped_reason=(
                safety_decision.reason
            ),
        )

    active_rows = (
        _list_active_source_opportunities(
            source_id=source_id
        )
    )

    missing_rows: list[
        dict[str, Any]
    ] = []

    for row in active_rows:
        source_reference = row.get(
            "source_reference"
        )

        record_id = row.get(
            "id"
        )

        if not isinstance(
            source_reference,
            str,
        ):
            continue

        if not isinstance(
            record_id,
            str,
        ):
            continue

        cleaned_source_reference = (
            source_reference.strip()
        )

        if not cleaned_source_reference:
            continue

        if not cleaned_source_reference.isdigit():
            # Lokale fixtures en andere niet-productiereferenties
            # mogen niet door de productie-closure worden gewijzigd.
            continue

        if (
            cleaned_source_reference
            not in cleaned_references
        ):
            missing_rows.append(
                row
            )

    client = get_supabase_client()

    for start_index in range(
        0,
        len(missing_rows),
        update_batch_size,
    ):
        current_batch = missing_rows[
            start_index:
            start_index + update_batch_size
        ]

        record_ids = [
            row["id"]
            for row in current_batch
        ]

        (
            client.table("raw_opportunities")
            .update(
                {
                    "source_status": "closed",
                    "processing_status": "pending",
                    "latest_fetch_run_id": str(
                        fetch_run_id
                    ),
                }
            )
            .in_(
                "id",
                record_ids,
            )
            .execute()
        )

    closed_references = tuple(
        str(row["source_reference"])
        for row in missing_rows
    )

    return MissingOpportunityClosureResult(
        executed=True,
        closed_count=len(
            closed_references
        ),
        closed_references=(
            closed_references
        ),
        current_discovered_count=(
            current_discovered_count
        ),
        previous_discovered_count=(
            previous_discovered_count
        ),
        minimum_allowed_count=(
            safety_decision.minimum_allowed_count
        ),
        skipped_reason=None,
    )
