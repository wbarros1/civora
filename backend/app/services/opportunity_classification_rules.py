"""Deterministische regels voor Civora vakgroepclassificatie."""

from dataclasses import dataclass

from backend.app.schemas.opportunity_classification import (
    OpportunityClassificationEnvelope,
    OpportunityVakgroep,
    Vakgroep,
)


RELEVANCE_THRESHOLD = 60
MAX_MATCHES = 3


VAKGROEP_ORDER: tuple[
    Vakgroep,
    ...,
] = (
    "procesmanagement",
    "data_ai",
    "ict",
    "finance",
)


@dataclass(
    frozen=True,
    slots=True,
)
class RelevantVakgroep:
    """Eén vakgroep die de relevantiedrempel haalt."""

    vakgroep: Vakgroep
    relevance_score: int
    reason: str


@dataclass(
    frozen=True,
    slots=True,
)
class ClassificationDecision:
    """Deterministisch afgeleide classificatie."""

    primary_vakgroep: OpportunityVakgroep

    matches: tuple[
        RelevantVakgroep,
        ...,
    ]

    classification_confidence: float

    review_reasons: tuple[
        str,
        ...,
    ]

    relevance_threshold: int
    max_matches: int


def derive_classification(
    classification: OpportunityClassificationEnvelope,
    *,
    relevance_threshold: int = RELEVANCE_THRESHOLD,
    max_matches: int = MAX_MATCHES,
) -> ClassificationDecision:
    """Leid primary en matches af uit vier ruwe scores."""

    if not (
        0
        <= relevance_threshold
        <= 100
    ):
        raise ValueError(
            "relevance_threshold moet "
            "tussen 0 en 100 liggen."
        )

    if not (
        1
        <= max_matches
        <= 4
    ):
        raise ValueError(
            "max_matches moet "
            "tussen 1 en 4 liggen."
        )

    scores = {
        vakgroep: getattr(
            classification,
            vakgroep,
        )
        for vakgroep
        in VAKGROEP_ORDER
    }

    order_index = {
        vakgroep: index
        for index, vakgroep
        in enumerate(
            VAKGROEP_ORDER
        )
    }

    ranked = sorted(
        VAKGROEP_ORDER,
        key=lambda vakgroep: (
            -scores[
                vakgroep
            ].relevance_score,
            order_index[
                vakgroep
            ],
        ),
    )

    relevant = [
        vakgroep
        for vakgroep in ranked
        if (
            scores[
                vakgroep
            ].relevance_score
            >= relevance_threshold
        )
    ][
        :max_matches
    ]

    review_reasons = list(
        classification.review_reasons
    )

    top_score = (
        scores[
            ranked[0]
        ].relevance_score
    )

    tied_top = [
        vakgroep
        for vakgroep in ranked
        if (
            scores[
                vakgroep
            ].relevance_score
            == top_score
        )
    ]

    if (
        len(tied_top) > 1
        and top_score >= relevance_threshold
    ):
        review_reasons.append(
            "Meerdere vakgroepen hebben "
            "dezelfde hoogste relevantiescore."
        )

    if not relevant:
        primary_vakgroep: (
            OpportunityVakgroep
        ) = "overige"

        matches: tuple[
            RelevantVakgroep,
            ...,
        ] = ()

    else:
        primary_vakgroep = (
            relevant[0]
        )

        matches = tuple(
            RelevantVakgroep(
                vakgroep=vakgroep,
                relevance_score=(
                    scores[
                        vakgroep
                    ].relevance_score
                ),
                reason=(
                    scores[
                        vakgroep
                    ].reason
                ),
            )
            for vakgroep
            in relevant
        )

    return ClassificationDecision(
        primary_vakgroep=(
            primary_vakgroep
        ),
        matches=matches,
        classification_confidence=(
            classification
            .classification_confidence
        ),
        review_reasons=tuple(
            review_reasons
        ),
        relevance_threshold=(
            relevance_threshold
        ),
        max_matches=(
            max_matches
        ),
    )