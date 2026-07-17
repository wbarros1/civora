"""Pydantic-modellen voor databronnen."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


SourceType = Literal[
    "api",
    "rss",
    "html",
    "hybrid",
]


class Source(BaseModel):
    """Een geconfigureerde bron voor inhuuropdrachten."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    code: str
    name: str
    base_url: str
    source_type: SourceType
    is_active: bool
    fetch_interval_minutes: int

    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None

    configuration: dict[str, Any]

    created_at: datetime
    updated_at: datetime