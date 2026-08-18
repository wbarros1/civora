"""Gedeelde pipeline voor Civora vakgroepclassificatie."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from backend.app.repositories.opportunity_classifications import (
    get_existing_classification,
    get_latest_classification_context,
    persist_classification,
)
from backend.app.services.opportunity_classification_input import (
    build_classification_input,
    render_classification_input,
)
from backend.app.services.opportunity_classification_rules import (
    VAKGROEP_ORDER,
    derive_classification,
)
from backend.app.services.opportunity_classifier import (
    CLASSIFIER_VERSION,
    classify_opportunity_with_llm,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ClassificationExecutionResult:
    """Resultaat van één classificatiepoging."""

    source_reference: str
    outcome: str

    extraction_run_id: str
    structured_opportunity_id: str

    classification_id: str | None

    output_payload: (
        dict[str, Any] | None
    )


def _build_score_payloads(
    classification: Any,
) -> list[dict[str, Any]]:
    """Maak de vier database-scorepayloads."""

    return [
        {
            "vakgroep": vakgroep,
            "relevance_score": (
                getattr(
                    classification,
                    vakgroep,
                )
                .relevance_score
            ),
            "reason": (
                getattr(
                    classification,
                    vakgroep,
                )
                .reason
            ),
        }
        for vakgroep
        in VAKGROEP_ORDER
    ]


def execute_opportunity_classification(
    source_reference: str,
) -> ClassificationExecutionResult:
    """Voer één volledige Civora-classificatie uit."""

    context = (
        get_latest_classification_context(
            source_reference
        )
    )

    existing = (
        get_existing_classification(
            extraction_run_id=(
                context.extraction_run_id
            ),
            classifier_version=(
                CLASSIFIER_VERSION
            ),
        )
    )

    if existing is not None:
        return ClassificationExecutionResult(
            source_reference=(
                context.source_reference
            ),
            outcome="skipped",
            extraction_run_id=(
                context.extraction_run_id
            ),
            structured_opportunity_id=(
                context
                .structured_opportunity_id
            ),
            classification_id=str(
                existing["id"]
            ),
            output_payload={
                "classification": (
                    existing
                ),
            },
        )

    classification_input = (
        build_classification_input(
            context.opportunity
        )
    )

    rendered_input = (
        render_classification_input(
            classification_input
        )
    )

    input_hash = sha256(
        rendered_input.encode(
            "utf-8"
        )
    ).hexdigest()

    classification_result = (
        classify_opportunity_with_llm(
            classification_input
        )
    )

    decision = derive_classification(
        classification_result
        .classification
    )

    score_payloads = (
        _build_score_payloads(
            classification_result
            .classification
        )
    )

    stored = persist_classification(
        extraction_run_id=(
            context.extraction_run_id
        ),
        structured_opportunity_id=(
            context
            .structured_opportunity_id
        ),
        primary_vakgroep=(
            decision.primary_vakgroep
        ),
        classification_confidence=(
            decision
            .classification_confidence
        ),
        classifier_version=(
            classification_result
            .classifier_version
        ),
        relevance_threshold=(
            decision
            .relevance_threshold
        ),
        max_matches=(
            decision.max_matches
        ),
        review_reasons=list(
            decision.review_reasons
        ),
        scores=score_payloads,
    )

    matches = [
        {
            "vakgroep": (
                match.vakgroep
            ),
            "relevance_score": (
                match.relevance_score
            ),
            "reason": (
                match.reason
            ),
        }
        for match in decision.matches
    ]

    output_payload = {
        "source_reference": (
            context.source_reference
        ),
        "extraction_run_id": (
            context.extraction_run_id
        ),
        "structured_opportunity_id": (
            context
            .structured_opportunity_id
        ),
        "input_hash": input_hash,
        "classifier_version": (
            classification_result
            .classifier_version
        ),
        "response_id": (
            classification_result
            .response_id
        ),
        "model_name": (
            classification_result
            .model_name
        ),
        "usage": {
            "input_tokens": (
                classification_result
                .input_tokens
            ),
            "output_tokens": (
                classification_result
                .output_tokens
            ),
            "total_tokens": (
                classification_result
                .total_tokens
            ),
        },
        "scores": score_payloads,
        "decision": {
            "primary_vakgroep": (
                decision
                .primary_vakgroep
            ),
            "matches": matches,
            "classification_confidence": (
                decision
                .classification_confidence
            ),
            "review_reasons": list(
                decision.review_reasons
            ),
            "relevance_threshold": (
                decision
                .relevance_threshold
            ),
            "max_matches": (
                decision.max_matches
            ),
        },
        "database": {
            "classification_id": str(
                stored["id"]
            ),
        },
    }

    return ClassificationExecutionResult(
        source_reference=(
            context.source_reference
        ),
        outcome="classified",
        extraction_run_id=(
            context.extraction_run_id
        ),
        structured_opportunity_id=(
            context
            .structured_opportunity_id
        ),
        classification_id=str(
            stored["id"]
        ),
        output_payload=(
            output_payload
        ),
    )