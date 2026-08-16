"""Tests voor Civora-gebruikersschema's."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.user import (
    ProfileUpdate,
)


def test_valid_profile_update() -> None:
    """Een geldige profielwijziging wordt geaccepteerd."""

    profile = ProfileUpdate(
        full_name="  Wilson Test  ",
        vakgroep="data_ai",
    )

    assert (
        profile.full_name
        == "Wilson Test"
    )

    assert (
        profile.vakgroep
        == "data_ai"
    )


def test_rejects_empty_name() -> None:
    """Een lege naam wordt geweigerd."""

    with pytest.raises(
        ValidationError
    ):
        ProfileUpdate(
            full_name="   ",
            vakgroep="ict",
        )


def test_rejects_invalid_vakgroep() -> None:
    """Een onbekende vakgroep wordt geweigerd."""

    with pytest.raises(
        ValidationError
    ):
        ProfileUpdate(
            full_name="Wilson Test",
            vakgroep="marketing",
        )