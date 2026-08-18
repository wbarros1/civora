"""Tests voor classificatie-input."""

from backend.app.services.opportunity_classification_input import (
    build_classification_input,
    render_classification_input,
)


def test_builds_classification_input() -> None:
    """Alle relevante velden worden meegenomen."""

    result = build_classification_input(
        {
            "title":
                "  Data Engineer  ",
            "client_name":
                "Gemeente Rotterdam",
            "description":
                "Bouwen van een dataplatform.",
            "requirements": [
                "Python",
                "Python",
                "Azure",
            ],
            "wishes": [],
            "competencies": [
                "Analytisch"
            ],
            "skills": [
                "SQL"
            ],
        }
    )

    assert (
        result.title
        == "Data Engineer"
    )

    assert result.requirements == [
        "Python",
        "Azure",
    ]


def test_render_is_deterministic() -> None:
    """Dezelfde inhoud geeft dezelfde JSON-input."""

    opportunity = {
        "title":
            "Projectmanager Dataplatform",
        "requirements": [
            "Projectmanagement",
            "Data",
        ],
    }

    first = (
        render_classification_input(
            build_classification_input(
                opportunity
            )
        )
    )

    second = (
        render_classification_input(
            build_classification_input(
                opportunity
            )
        )
    )

    assert first == second