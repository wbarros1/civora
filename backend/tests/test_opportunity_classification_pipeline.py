"""Tests voor de Civora classificatiepipeline."""

from types import SimpleNamespace

from backend.app.schemas.opportunity_classification import (
    OpportunityClassificationEnvelope,
)
from backend.app.services import (
    opportunity_classification_pipeline
    as pipeline,
)


def build_llm_classification(
) -> OpportunityClassificationEnvelope:
    """Maak een volledige classifier-output."""

    return OpportunityClassificationEnvelope(
        procesmanagement={
            "relevance_score": 88,
            "reason": "Projectmanagement is belangrijk.",
        },
        data_ai={
            "relevance_score": 72,
            "reason": "Data is inhoudelijk relevant.",
        },
        ict={
            "relevance_score": 40,
            "reason": "ICT is ondersteunend.",
        },
        finance={
            "relevance_score": 5,
            "reason": "Geen financiële kernwerkzaamheden.",
        },
        classification_confidence=0.9,
        review_reasons=[],
    )


def test_builds_all_four_score_payloads() -> None:
    """Persistence ontvangt altijd alle vier scores."""

    scores = pipeline._build_score_payloads(
        build_llm_classification()
    )

    assert len(scores) == 4

    assert {
        score["vakgroep"]
        for score in scores
    } == {
        "procesmanagement",
        "data_ai",
        "ict",
        "finance",
    }


def test_existing_classification_skips_llm(
    monkeypatch,
) -> None:
    """Een bestaande run+versie veroorzaakt geen LLM-call."""

    monkeypatch.setattr(
        pipeline,
        "get_latest_classification_context",
        lambda reference: SimpleNamespace(
            extraction_run_id="run-1",
            structured_opportunity_id="structured-1",
            source_reference=reference,
            opportunity={},
        ),
    )

    monkeypatch.setattr(
        pipeline,
        "get_existing_classification",
        lambda **kwargs: {
            "id": "classification-1",
            "primary_vakgroep":
                "procesmanagement",
            "scores": [],
        },
    )

    def fail_if_called(
        *_args,
        **_kwargs,
    ):
        raise AssertionError(
            "LLM mag niet worden aangeroepen."
        )

    monkeypatch.setattr(
        pipeline,
        "classify_opportunity_with_llm",
        fail_if_called,
    )

    result = (
        pipeline
        .execute_opportunity_classification(
            "30412"
        )
    )

    assert (
        result.outcome
        == "skipped"
    )

    assert (
        result.classification_id
        == "classification-1"
    )