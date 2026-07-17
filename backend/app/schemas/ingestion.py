"""Pydantic-modellen voor de ingestion-opslaglaag."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


FetchRunStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "partial",
    "failed",
]

FetchTrigger = Literal[
    "manual",
    "scheduled",
    "api",
]

RawFormat = Literal[
    "html",
    "json",
    "xml",
    "text",
]

SourceOpportunityStatus = Literal[
    "active",
    "closed",
    "removed",
    "unknown",
]

ProcessingStatus = Literal[
    "pending",
    "extracted",
    "review_required",
    "failed",
    "ignored",
]

RawUpsertAction = Literal[
    "created",
    "changed",
    "unchanged",
]


class FetchRun(BaseModel):
    """Een geregistreerde ophaalactie voor één databron."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    source_id: UUID

    status: FetchRunStatus
    triggered_by: FetchTrigger

    request_url: str | None = None
    http_status: int | None = None

    started_at: datetime
    finished_at: datetime | None = None

    items_discovered: int
    items_new: int
    items_changed: int
    items_unchanged: int
    items_failed: int

    error_message: str | None = None
    metadata: dict[str, Any]

    created_at: datetime
    updated_at: datetime


class RawOpportunity(BaseModel):
    """De meest recente ruwe versie van een bronopdracht."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    source_id: UUID

    source_reference: str
    source_url: str
    title_hint: str | None = None

    raw_format: RawFormat
    raw_content: str
    content_hash: str
    normalized_content_hash: str | None = None

    source_status: SourceOpportunityStatus
    processing_status: ProcessingStatus

    latest_fetch_run_id: UUID | None = None

    published_at: datetime | None = None
    closed_at: datetime | None = None

    first_seen_at: datetime
    last_seen_at: datetime

    metadata: dict[str, Any]

    created_at: datetime
    updated_at: datetime


class RawOpportunityVersion(BaseModel):
    """Een onveranderlijke versie van ruwe broninhoud."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    raw_opportunity_id: UUID
    fetch_run_id: UUID | None = None

    version_number: int

    source_url: str
    raw_format: RawFormat
    raw_content: str
    content_hash: str
    normalized_content_hash: str | None = None

    metadata: dict[str, Any]
    created_at: datetime


class RawUpsertResult(BaseModel):
    """Resultaat van het opslaan van ruwe brondata."""

    action: RawUpsertAction
    opportunity: RawOpportunity
    version_number: int