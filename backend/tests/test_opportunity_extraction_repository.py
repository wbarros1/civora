"""Tests voor extractie-idempotentie."""

import pytest

from backend.app.repositories.opportunity_extractions import (
    build_extraction_idempotency_key,
)


def test_idempotency_key_is_stable() -> None:
    """Dezelfde invoer levert steeds dezelfde sleutel op."""

    first_key = (
        build_extraction_idempotency_key(
            raw_opportunity_id="raw-123",
            input_hash="content-hash",
            prompt_version=(
                "flextender-extraction-v3"
            ),
            requested_model="gpt-5-mini",
            postprocessing_version=(
                "opportunity-postprocessing-v1"
            ),
        )
    )

    second_key = (
        build_extraction_idempotency_key(
            raw_opportunity_id="raw-123",
            input_hash="content-hash",
            prompt_version=(
                "flextender-extraction-v3"
            ),
            requested_model="gpt-5-mini",
            postprocessing_version=(
                "opportunity-postprocessing-v1"
            ),
        )
    )

    assert first_key == second_key
    assert len(first_key) == 64


@pytest.mark.parametrize(
    (
        "changed_field",
        "changed_value",
    ),
    [
        (
            "input_hash",
            "new-content-hash",
        ),
        (
            "prompt_version",
            "flextender-extraction-v4",
        ),
        (
            "requested_model",
            "another-model",
        ),
        (
            "raw_opportunity_id",
            "raw-456",
        ),
        (
            "postprocessing_version",
            "opportunity-postprocessing-v2",
        ),
    ],
)
def test_idempotency_key_changes(
    changed_field: str,
    changed_value: str,
) -> None:
    """Een relevante wijziging levert een nieuwe sleutel op."""

    arguments = {
        "raw_opportunity_id": (
            "raw-123"
        ),
        "input_hash": (
            "content-hash"
        ),
        "prompt_version": (
            "flextender-extraction-v3"
        ),
        "requested_model": (
            "gpt-5-mini"
        ),
        "postprocessing_version": (
            "opportunity-postprocessing-v1"
        ),
    }

    original_key = (
        build_extraction_idempotency_key(
            **arguments
        )
    )

    arguments[changed_field] = (
        changed_value
    )

    changed_key = (
        build_extraction_idempotency_key(
            **arguments
        )
    )

    assert changed_key != original_key

@pytest.mark.parametrize(
    "empty_field",
    [
        "raw_opportunity_id",
        "input_hash",
        "prompt_version",
        "requested_model",
        "postprocessing_version",
    ],
)
def test_idempotency_key_rejects_empty_values(
    empty_field: str,
) -> None:
    """Lege onderdelen zijn niet toegestaan."""

    arguments = {
        "raw_opportunity_id": "raw-123",
        "input_hash": "content-hash",
        "prompt_version": (
            "flextender-extraction-v3"
        ),
        "requested_model": "gpt-5-mini",
        "postprocessing_version": (
            "opportunity-postprocessing-v1"
        ),
    }

    arguments[empty_field] = ""

    with pytest.raises(
        ValueError
    ):
        build_extraction_idempotency_key(
            **arguments
        )