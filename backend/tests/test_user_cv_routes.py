"""Tests voor de API-routes van het basis-CV."""

import asyncio

import pytest
from fastapi import HTTPException

from backend.app.api.routes import (
    user_cv as user_cv_route,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)


IDENTITY = AuthenticatedIdentity(
    id="user-1",
    email="test@example.com",
)


CV_ROW = {
    "id": "cv-1",
    "user_id": "user-1",
    "original_filename": "Mijn CV.pdf",
    "storage_bucket": "user-cvs",
    "storage_path": (
        "user-1/cv-1/source.pdf"
    ),
    "mime_type": "application/pdf",
    "file_size_bytes": 1234,
    "sha256": (
        "a" * 64
    ),
    "processing_status": "uploaded",
    "processing_error": None,
    "is_active": True,
    "uploaded_at": (
        "2026-08-21T12:00:00+00:00"
    ),
    "created_at": (
        "2026-08-21T12:00:00+00:00"
    ),
    "updated_at": (
        "2026-08-21T12:00:00+00:00"
    ),
}


def test_get_current_user_cv(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        user_cv_route,
        "get_active_user_cv",
        lambda user_id: CV_ROW,
    )

    result = asyncio.run(
        user_cv_route
        .get_current_user_cv(
            identity=IDENTITY
        )
    )

    assert result is not None
    assert result.id == "cv-1"
    assert (
        result.original_filename
        == "Mijn CV.pdf"
    )


def test_get_current_user_cv_returns_none(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        user_cv_route,
        "get_active_user_cv",
        lambda user_id: None,
    )

    result = asyncio.run(
        user_cv_route
        .get_current_user_cv(
            identity=IDENTITY
        )
    )

    assert result is None


def test_download_current_user_cv(
    monkeypatch,
) -> None:
    captured: dict = {}

    monkeypatch.setattr(
        user_cv_route,
        "get_active_user_cv",
        lambda user_id: CV_ROW,
    )

    def fake_download(
        *,
        storage_path: str,
    ) -> bytes:
        captured[
            "storage_path"
        ] = storage_path

        return b"%PDF-test"

    monkeypatch.setattr(
        user_cv_route,
        "download_user_cv_file",
        fake_download,
    )

    response = asyncio.run(
        user_cv_route
        .download_current_user_cv(
            identity=IDENTITY
        )
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.body
        == b"%PDF-test"
    )

    assert (
        captured["storage_path"]
        == "user-1/cv-1/source.pdf"
    )

    assert (
        "Mijn%20CV.pdf"
        in response.headers[
            "content-disposition"
        ]
    )

    assert (
        response.headers[
            "cache-control"
        ]
        == "private, no-store"
    )


def test_delete_cv_in_use_is_blocked(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        user_cv_route,
        "get_active_user_cv",
        lambda user_id: CV_ROW,
    )

    monkeypatch.setattr(
        user_cv_route,
        "is_user_cv_in_use",
        lambda **kwargs: True,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        asyncio.run(
            user_cv_route
            .delete_current_user_cv(
                identity=IDENTITY
            )
        )

    assert (
        exc_info.value.status_code
        == 409
    )


def test_delete_current_user_cv(
    monkeypatch,
) -> None:
    actions: list[str] = []

    monkeypatch.setattr(
        user_cv_route,
        "get_active_user_cv",
        lambda user_id: CV_ROW,
    )

    monkeypatch.setattr(
        user_cv_route,
        "is_user_cv_in_use",
        lambda **kwargs: False,
    )

    def fake_remove(
        *,
        storage_path: str,
    ) -> None:
        assert (
            storage_path
            == "user-1/cv-1/source.pdf"
        )

        actions.append(
            "storage"
        )

    def fake_delete(
        *,
        user_id: str,
        cv_id: str,
    ) -> None:
        assert (
            user_id
            == "user-1"
        )

        assert (
            cv_id
            == "cv-1"
        )

        actions.append(
            "database"
        )

    monkeypatch.setattr(
        user_cv_route,
        "remove_user_cv_file",
        fake_remove,
    )

    monkeypatch.setattr(
        user_cv_route,
        "delete_user_cv_record",
        fake_delete,
    )

    response = asyncio.run(
        user_cv_route
        .delete_current_user_cv(
            identity=IDENTITY
        )
    )

    assert (
        response.status_code
        == 204
    )

    assert actions == [
        "storage",
        "database",
    ]