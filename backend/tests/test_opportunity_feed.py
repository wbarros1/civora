"""Tests voor de gepersonaliseerde opportunity-feed."""

import asyncio

from backend.app.api.routes import (
    opportunities as opportunities_route,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)
from backend.app.services.opportunity_classifier import (
    CLASSIFIER_VERSION,
)


def execute_route(
    *,
    identity: AuthenticatedIdentity,
    feed: str,
):
    """Roep de route rechtstreeks aan."""

    return asyncio.run(
        opportunities_route.get_opportunities(
            identity=identity,
            feed=feed,
            search=None,
            client=None,
            province=None,
            work_arrangement=None,
            employment_relationship=None,
            application_status=None,
            limit=20,
            offset=0,
        )
    )


def test_for_you_uses_profile_vakgroep(
    monkeypatch,
) -> None:
    """De persoonlijke feed gebruikt server-side de profielvakgroep."""

    captured: dict = {}

    monkeypatch.setattr(
        opportunities_route,
        "get_profile",
        lambda user_id: {
            "id": user_id,
            "full_name": "Test User",
            "role": "user",
            "vakgroep": "data_ai",
        },
    )

    def fake_list_opportunities(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return (
            [
                {
                    "id": "opportunity-1",
                    "source_reference": "31342",
                    "title": "Data Engineer",
                    "source_status": "active",
                    "application_status": "open",
                    "primary_vakgroep": "data_ai",
                    "matched_vakgroep": "data_ai",
                    "relevance_score": 95,
                    "classification_confidence": 0.9,
                }
            ],
            False,
        )

    monkeypatch.setattr(
        opportunities_route,
        "list_opportunities",
        fake_list_opportunities,
    )

    response = execute_route(
        identity=AuthenticatedIdentity(
            id="user-1",
            email="test@example.com",
        ),
        feed="for_you",
    )

    assert (
        captured["user_vakgroep"]
        == "data_ai"
    )

    assert (
        captured["classifier_version"]
        == CLASSIFIER_VERSION
    )

    assert (
        response.feed
        == "for_you"
    )

    assert (
        response.vakgroep
        == "data_ai"
    )

    assert (
        response.items[0]
        .relevance_score
        == 95
    )


def test_all_feed_does_not_use_profile_vakgroep(
    monkeypatch,
) -> None:
    """Alle opdrachten gebruikt geen profielvakgroepfilter."""

    captured: dict = {}

    def fail_if_profile_called(
        _user_id: str,
    ):
        raise AssertionError(
            "Profiel mag voor feed=all "
            "niet nodig zijn."
        )

    monkeypatch.setattr(
        opportunities_route,
        "get_profile",
        fail_if_profile_called,
    )

    def fake_list_opportunities(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return (
            [
                {
                    "id": "opportunity-2",
                    "source_reference": "31351",
                    "title": (
                        "Technisch Specialist "
                        "Civiele Techniek"
                    ),
                    "source_status": "active",
                    "application_status": "open",
                }
            ],
            False,
        )

    monkeypatch.setattr(
        opportunities_route,
        "list_opportunities",
        fake_list_opportunities,
    )

    response = execute_route(
        identity=AuthenticatedIdentity(
            id="user-1",
            email="test@example.com",
        ),
        feed="all",
    )

    assert (
        captured["user_vakgroep"]
        is None
    )

    assert (
        captured["classifier_version"]
        is None
    )

    assert (
        response.feed
        == "all"
    )

    assert (
        response.vakgroep
        is None
    )