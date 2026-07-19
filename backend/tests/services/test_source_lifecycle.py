"""Tests voor veilige missing-opportunity closure."""

from backend.app.services.source_lifecycle import (
    evaluate_missing_closure_safety,
)


def test_closure_requires_previous_full_run() -> None:
    """Zonder vergelijkingsbasis wordt niets gesloten."""

    decision = evaluate_missing_closure_safety(
        current_discovered_count=222,
        previous_discovered_count=None,
    )

    assert decision.allowed is False
    assert decision.reason is not None


def test_closure_allows_stable_discovery() -> None:
    """Een stabiele discovery mag closure uitvoeren."""

    decision = evaluate_missing_closure_safety(
        current_discovered_count=222,
        previous_discovered_count=222,
    )

    assert decision.allowed is True
    assert decision.minimum_allowed_count == 156
    assert decision.reason is None


def test_closure_blocks_large_drop() -> None:
    """Een onverwacht sterke daling blokkeert closure."""

    decision = evaluate_missing_closure_safety(
        current_discovered_count=80,
        previous_discovered_count=222,
    )

    assert decision.allowed is False
    assert decision.minimum_allowed_count == 156


def test_closure_accepts_exact_ratio_boundary() -> None:
    """De grens van 70 procent is toegestaan."""

    decision = evaluate_missing_closure_safety(
        current_discovered_count=140,
        previous_discovered_count=200,
    )

    assert decision.allowed is True
    assert decision.minimum_allowed_count == 140


def test_closure_obeys_absolute_minimum() -> None:
    """Ook bij een kleine vorige run geldt het absolute minimum."""

    decision = evaluate_missing_closure_safety(
        current_discovered_count=40,
        previous_discovered_count=50,
    )

    assert decision.allowed is False
    assert decision.minimum_allowed_count == 50