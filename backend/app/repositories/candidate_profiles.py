"""Databasefuncties voor gestructureerde kandidaatprofielen."""

from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)


CANDIDATE_PROFILE_COLUMNS = (
    "id,"
    "user_id,"
    "user_cv_id,"
    "schema_version,"
    "profile_data,"
    "provider,"
    "model_name,"
    "prompt_version,"
    "input_hash,"
    "input_token_count,"
    "output_token_count,"
    "total_token_count,"
    "validation_errors,"
    "extraction_confidence,"
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


def get_candidate_profile_by_cv(
    *,
    user_id: str,
    user_cv_id: str,
) -> dict[str, Any] | None:
    """Haal het kandidaatprofiel van één eigen CV op."""

    client = (
        get_supabase_client()
    )

    response = (
        client.table(
            "structured_candidate_profiles"
        )
        .select(
            CANDIDATE_PROFILE_COLUMNS
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "user_cv_id",
            user_cv_id,
        )
        .limit(1)
        .execute()
    )

    return _first_dict(
        response.data
    )


def upsert_candidate_profile(
    *,
    user_id: str,
    user_cv_id: str,
    schema_version: str,
    profile_data: dict[str, Any],
    provider: str,
    model_name: str,
    prompt_version: str,
    input_hash: str,
    input_token_count: int | None,
    output_token_count: int | None,
    total_token_count: int | None,
    validation_errors: list[
        dict[str, Any]
    ],
    extraction_confidence: float,
) -> dict[str, Any]:
    """
    Maak of vervang het gestructureerde profiel
    van één immutable CV-versie.
    """

    client = (
        get_supabase_client()
    )

    payload = {
        "user_id": (
            user_id
        ),
        "user_cv_id": (
            user_cv_id
        ),
        "schema_version": (
            schema_version
        ),
        "profile_data": (
            profile_data
        ),
        "provider": (
            provider
        ),
        "model_name": (
            model_name
        ),
        "prompt_version": (
            prompt_version
        ),
        "input_hash": (
            input_hash
        ),
        "input_token_count": (
            input_token_count
        ),
        "output_token_count": (
            output_token_count
        ),
        "total_token_count": (
            total_token_count
        ),
        "validation_errors": (
            validation_errors
        ),
        "extraction_confidence": (
            extraction_confidence
        ),
    }

    response = (
        client.table(
            "structured_candidate_profiles"
        )
        .upsert(
            payload,
            on_conflict="user_cv_id",
        )
        .execute()
    )

    row = _first_dict(
        response.data
    )

    if row is None:
        row = (
            get_candidate_profile_by_cv(
                user_id=user_id,
                user_cv_id=user_cv_id,
            )
        )

    if row is None:
        raise RuntimeError(
            "Kandidaatprofiel kon niet "
            "worden opgeslagen."
        )

    return row