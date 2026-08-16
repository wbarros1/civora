"""Tests voor opgeslagen zoekopdrachten."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.saved_search import (
    SavedSearchCreate,
)


def test_valid_saved_search() -> None:
    """Geldige filters worden geaccepteerd."""

    saved_search = SavedSearchCreate(
        name="  Hybride Data opdrachten  ",
        filters={
            "search": "  Data Engineer  ",
            "province": "Utrecht",
            "work_arrangement": "hybrid",
        },
    )

    assert (
        saved_search.name
        == "Hybride Data opdrachten"
    )

    assert (
        saved_search.filters.search
        == "Data Engineer"
    )


def test_rejects_empty_name() -> None:
    """Lege naam wordt geweigerd."""

    with pytest.raises(
        ValidationError
    ):
        SavedSearchCreate(
            name="   ",
            filters={},
        )


def test_rejects_invalid_work_arrangement() -> None:
    """Onbekende werkvorm wordt geweigerd."""

    with pytest.raises(
        ValidationError
    ):
        SavedSearchCreate(
            name="Test",
            filters={
                "work_arrangement":
                    "somewhere",
            },
        )