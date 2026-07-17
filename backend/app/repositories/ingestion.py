"""Databasequeries voor bronophalingen en ruwe opdrachten."""

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
)
from backend.app.services.content_hashing import calculate_content_hash


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
    content_hash = calculate_content_hash(raw_content)
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
            "source_status": "active",
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

    if existing_opportunity.content_hash == content_hash:
        update_payload = {
            "source_url": source_url,
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
        metadata=opportunity_metadata,
    )

    changed_payload = {
        "source_url": source_url,
        "title_hint": title_hint,
        "raw_format": raw_format,
        "raw_content": raw_content,
        "content_hash": content_hash,
        "processing_status": "pending",
        "latest_fetch_run_id": str(fetch_run_id),
        "published_at": (
            published_at.isoformat()
            if published_at
            else existing_data.get("published_at")
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