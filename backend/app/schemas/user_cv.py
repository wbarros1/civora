"""API-schema's voor basis-CV's."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


CvProcessingStatus = Literal[
    "uploaded",
    "processing",
    "ready",
    "failed",
]


class UserCvResponse(BaseModel):
    """Metadata van het actieve basis-CV."""

    id: str

    original_filename: str
    mime_type: str
    file_size_bytes: int

    processing_status: (
        CvProcessingStatus
    )

    is_active: bool

    uploaded_at: datetime