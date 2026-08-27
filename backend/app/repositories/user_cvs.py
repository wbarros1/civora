"""Databasefuncties voor gebruikers-CV's."""

from typing import Any
from backend.app.schemas.user_cv import (
    CvProcessingStatus,
)

from backend.app.database.client import (
    get_supabase_client,
)


USER_CV_COLUMNS = (
    "id,"
    "user_id,"
    "original_filename,"
    "storage_bucket,"
    "storage_path,"
    "mime_type,"
    "file_size_bytes,"
    "sha256,"
    "processing_status,"
    "processing_error,"
    "is_active,"
    "uploaded_at,"
    "created_at,"
    "updated_at"
)


def _first_dict(
    data: Any,
) -> dict[str, Any] | None:
    """Geef de eerste dictionary uit een response."""

    if isinstance(
        data,
        list,
    ):
        for row in data:
            if isinstance(
                row,
                dict,
            ):
                return row

    if isinstance(
        data,
        dict,
    ):
        return data

    return None


def get_active_user_cv(
    user_id: str,
) -> dict[str, Any] | None:
    """Haal het actieve basis-CV op."""

    client = (
        get_supabase_client()
    )

    response = (
        client.table(
            "user_cvs"
        )
        .select(
            USER_CV_COLUMNS
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "is_active",
            True,
        )
        .limit(1)
        .execute()
    )

    return _first_dict(
        response.data
    )


def get_user_cv(
    *,
    user_id: str,
    cv_id: str,
) -> dict[str, Any] | None:
    """Haal één CV op, beperkt tot de eigenaar."""

    client = (
        get_supabase_client()
    )

    response = (
        client.table(
            "user_cvs"
        )
        .select(
            USER_CV_COLUMNS
        )
        .eq(
            "id",
            cv_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    return _first_dict(
        response.data
    )


def create_user_cv(
    *,
    cv_id: str,
    user_id: str,
    original_filename: str,
    storage_path: str,
    mime_type: str,
    file_size_bytes: int,
    sha256_hash: str,
) -> dict[str, Any]:
    """Maak een nieuwe, aanvankelijk inactieve CV-versie."""

    client = (
        get_supabase_client()
    )

    response = (
        client.table(
            "user_cvs"
        )
        .insert(
            {
                "id": cv_id,
                "user_id": user_id,
                "original_filename": (
                    original_filename
                ),
                "storage_bucket": (
                    "user-cvs"
                ),
                "storage_path": (
                    storage_path
                ),
                "mime_type": (
                    mime_type
                ),
                "file_size_bytes": (
                    file_size_bytes
                ),
                "sha256": (
                    sha256_hash
                ),
                "processing_status": (
                    "uploaded"
                ),
                "is_active": False,
            }
        )
        .execute()
    )

    row = _first_dict(
        response.data
    )

    if row is None:
        raise RuntimeError(
            "Nieuwe CV-record kon niet "
            "worden aangemaakt."
        )

    return row


def activate_user_cv(
    *,
    user_id: str,
    cv_id: str,
) -> dict[str, Any]:
    """Activeer één CV atomair via PostgreSQL."""

    client = (
        get_supabase_client()
    )

    (
        client.rpc(
            "activate_user_cv",
            {
                "p_user_id": (
                    user_id
                ),
                "p_user_cv_id": (
                    cv_id
                ),
            },
        )
        .execute()
    )

    row = get_user_cv(
        user_id=user_id,
        cv_id=cv_id,
    )

    if row is None:
        raise RuntimeError(
            "Geactiveerd CV kon niet "
            "worden teruggelezen."
        )

    if not row.get(
        "is_active"
    ):
        raise RuntimeError(
            "CV is na activatie niet actief."
        )

    return row


def delete_user_cv_record(
    *,
    user_id: str,
    cv_id: str,
) -> None:
    """Verwijder een CV-record tijdens rollback/cleanup."""

    client = (
        get_supabase_client()
    )

    (
        client.table(
            "user_cvs"
        )
        .delete()
        .eq(
            "id",
            cv_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

def is_user_cv_in_use(
    *,
    user_id: str,
    cv_id: str,
) -> bool:
    """
    Controleer of een CV al wordt gebruikt
    door een documentgeneratie.
    """

    client = (
        get_supabase_client()
    )

    response = (
        client.table(
            "application_generation_runs"
        )
        .select(
            "id"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "user_cv_id",
            cv_id,
        )
        .limit(1)
        .execute()
    )

    rows = (
        response.data or []
    )

    return bool(
        rows
    )


def update_user_cv_processing_status(
    *,
    user_id: str,
    cv_id: str,
    status: CvProcessingStatus,
    processing_error: str | None = None,
) -> dict[str, Any]:
    """
    Werk de verwerkingsstatus van één
    gebruikers-CV bij.
    """

    client = (
        get_supabase_client()
    )

    error_value = (
        processing_error[:1000]
        if processing_error
        else None
    )

    (
        client.table(
            "user_cvs"
        )
        .update(
            {
                "processing_status": (
                    status
                ),
                "processing_error": (
                    error_value
                ),
            }
        )
        .eq(
            "id",
            cv_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    row = get_user_cv(
        user_id=user_id,
        cv_id=cv_id,
    )

    if row is None:
        raise RuntimeError(
            "Bijgewerkt CV kon niet "
            "worden teruggelezen."
        )

    return row