"""Tests voor automatische classificatie na extraction."""

from types import SimpleNamespace

from backend.app.services import (
    opportunity_extraction_pipeline
    as pipeline,
)


def test_post_extraction_classification_succeeds(
    monkeypatch,
) -> None:
    """Een classifier-resultaat wordt correct doorgegeven."""

    monkeypatch.setattr(
        pipeline,
        "execute_opportunity_classification",
        lambda reference: SimpleNamespace(
            outcome="classified",
            classification_id=(
                "classification-1"
            ),
        ),
    )

    result = (
        pipeline
        .execute_post_extraction_classification(
            "31342"
        )
    )

    assert (
        result.outcome
        == "classified"
    )

    assert (
        result.classification_id
        == "classification-1"
    )

    assert result.error is None


def test_post_extraction_classification_failure_is_isolated(
    monkeypatch,
) -> None:
    """Een classifier-fout wordt teruggegeven en niet geraised."""

    def fail(
        _reference: str,
    ):
        raise RuntimeError(
            "Tijdelijke classifierfout"
        )

    monkeypatch.setattr(
        pipeline,
        "execute_opportunity_classification",
        fail,
    )

    result = (
        pipeline
        .execute_post_extraction_classification(
            "31342"
        )
    )

    assert (
        result.outcome
        == "failed"
    )

    assert (
        result.classification_id
        is None
    )

    assert (
        result.error
        is not None
    )

    assert (
        "Tijdelijke classifierfout"
        in result.error
    )