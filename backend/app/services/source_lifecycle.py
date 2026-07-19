"""Veiligheidsregels voor de levenscyclus van bronopdrachten."""

import math
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class MissingClosureSafetyDecision:
    """Resultaat van de veiligheidscontrole."""

    allowed: bool
    current_discovered_count: int
    previous_discovered_count: int | None
    minimum_allowed_count: int | None
    reason: str | None


def evaluate_missing_closure_safety(
    *,
    current_discovered_count: int,
    previous_discovered_count: int | None,
    minimum_discovered_count: int = 50,
    minimum_previous_ratio: float = 0.70,
) -> MissingClosureSafetyDecision:
    """
    Controleer of verdwenen opdrachten veilig gesloten mogen worden.

    Er moet een eerdere volledige succesvolle run zijn. Daarnaast
    moet de huidige discovery zowel een absoluut minimum als een
    minimumpercentage van de vorige run bevatten.
    """

    if current_discovered_count < 0:
        raise ValueError(
            "current_discovered_count mag niet negatief zijn."
        )

    if minimum_discovered_count < 1:
        raise ValueError(
            "minimum_discovered_count moet minimaal 1 zijn."
        )

    if not 0 < minimum_previous_ratio <= 1:
        raise ValueError(
            "minimum_previous_ratio moet groter dan 0 "
            "en maximaal 1 zijn."
        )

    if previous_discovered_count is None:
        return MissingClosureSafetyDecision(
            allowed=False,
            current_discovered_count=(
                current_discovered_count
            ),
            previous_discovered_count=None,
            minimum_allowed_count=None,
            reason=(
                "Er is nog geen eerdere succesvolle "
                "volledige run als vergelijkingsbasis."
            ),
        )

    if previous_discovered_count < 1:
        return MissingClosureSafetyDecision(
            allowed=False,
            current_discovered_count=(
                current_discovered_count
            ),
            previous_discovered_count=(
                previous_discovered_count
            ),
            minimum_allowed_count=None,
            reason=(
                "De vorige volledige run bevatte "
                "geen geldige discoverytelling."
            ),
        )

    ratio_minimum = math.ceil(
        previous_discovered_count
        * minimum_previous_ratio
    )

    minimum_allowed_count = max(
        minimum_discovered_count,
        ratio_minimum,
    )

    if (
        current_discovered_count
        < minimum_allowed_count
    ):
        return MissingClosureSafetyDecision(
            allowed=False,
            current_discovered_count=(
                current_discovered_count
            ),
            previous_discovered_count=(
                previous_discovered_count
            ),
            minimum_allowed_count=(
                minimum_allowed_count
            ),
            reason=(
                "De huidige discovery is onverwacht klein: "
                f"{current_discovered_count} gevonden, "
                f"minimaal {minimum_allowed_count} vereist."
            ),
        )

    return MissingClosureSafetyDecision(
        allowed=True,
        current_discovered_count=(
            current_discovered_count
        ),
        previous_discovered_count=(
            previous_discovered_count
        ),
        minimum_allowed_count=(
            minimum_allowed_count
        ),
        reason=None,
    )