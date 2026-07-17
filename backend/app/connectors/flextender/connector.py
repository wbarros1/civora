"""Uitvoering van de eerste Flextender-connector."""

from collections import Counter
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from backend.app.connectors.flextender.client import (
    FlextenderHttpClient,
)
from backend.app.connectors.flextender.parser import (
    DiscoveredOpportunity,
    detect_source_status,
    discover_opportunities,
    parse_title_hint,
    validate_detail_page,
)
from backend.app.core.config import get_settings
from backend.app.repositories.ingestion import (
    create_fetch_run,
    finish_fetch_run,
    store_raw_opportunity,
)
from backend.app.repositories.sources import (
    get_source_by_code,
)


@dataclass(frozen=True, slots=True)
class FlextenderRunSummary:
    """Samenvatting van een connectorrun."""

    fetch_run_id: UUID
    discovered: int
    selected: int
    created: int
    changed: int
    unchanged: int
    failed: int
    errors: tuple[str, ...]


def _get_listing_urls(
    configuration: dict[str, Any],
) -> list[str]:
    """Lees de Flextender-overzichtspagina's uit."""

    configured_urls = configuration.get(
        "listing_urls"
    )

    if isinstance(configured_urls, list):
        valid_urls = [
            str(url)
            for url in configured_urls
            if isinstance(url, str)
            and url.strip()
        ]

        if valid_urls:
            return valid_urls

    return [
        "https://www.flextender.nl/opdrachten/",
        "https://www.flextender.nl/",
    ]


def run_flextender_connector(
    *,
    max_items: int | None = None,
) -> FlextenderRunSummary:
    """Haal een beperkte set openbare Flextender-opdrachten op."""

    settings = get_settings()
    source = get_source_by_code("flextender")

    selected_limit = (
        max_items
        if max_items is not None
        else settings.scraper_max_items_per_run
    )

    if selected_limit < 1:
        raise ValueError(
            "max_items moet minimaal 1 zijn."
        )

    if selected_limit > 100:
        raise ValueError(
            "max_items mag voor deze connector "
            "niet hoger zijn dan 100."
        )

    listing_urls = _get_listing_urls(
        source.configuration
    )

    request_delay = float(
        source.configuration.get(
            "request_delay_seconds",
            settings.scraper_request_delay_seconds,
        )
    )

    fetch_run = create_fetch_run(
        source_id=source.id,
        triggered_by="manual",
        request_url=listing_urls[0],
        metadata={
            "connector": "flextender",
            "listing_urls": listing_urls,
            "max_items": selected_limit,
        },
    )

    discovered_by_reference: dict[
        str,
        DiscoveredOpportunity,
    ] = {}

    discovery_results: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    errors: list[str] = []
    last_http_status: int | None = None

    try:
        with FlextenderHttpClient(
            user_agent=settings.user_agent,
            timeout_seconds=(
                settings.request_timeout_seconds
            ),
        ) as http_client:
            for listing_url in listing_urls:
                try:
                    response = http_client.get_html(
                        listing_url
                    )

                    last_http_status = (
                        response.status_code
                    )

                    discovered_on_page = (
                        discover_opportunities(
                            page_html=response.text,
                            page_url=str(response.url),
                        )
                    )

                    discovery_results.append(
                        {
                            "url": listing_url,
                            "final_url": str(response.url),
                            "http_status": (
                                response.status_code
                            ),
                            "found": len(
                                discovered_on_page
                            ),
                        }
                    )

                    for opportunity in (
                        discovered_on_page
                    ):
                        discovered_by_reference.setdefault(
                            opportunity.source_reference,
                            opportunity,
                        )

                except Exception as exc:
                    error_message = (
                        f"Overzichtspagina mislukt "
                        f"({listing_url}): {exc}"
                    )

                    errors.append(error_message)

                    discovery_results.append(
                        {
                            "url": listing_url,
                            "error": str(exc),
                            "found": 0,
                        }
                    )

            if not discovered_by_reference:
                raise RuntimeError(
                    "Er zijn geen Flextender-detail-URL's "
                    "gevonden op de ingestelde pagina's."
                )

            discovered_opportunities = list(
                discovered_by_reference.values()
            )

            selected_opportunities = (
                discovered_opportunities[
                    :selected_limit
                ]
            )

            for opportunity in selected_opportunities:
                try:
                    response = http_client.get_html(
                        opportunity.source_url,
                        delay_seconds=request_delay,
                    )

                    validate_detail_page(
                        page_html=response.text,
                        source_reference=(
                            opportunity.source_reference
                        ),
                    )

                    title_hint = parse_title_hint(
                        response.text
                    )

                    source_status = detect_source_status(
                        response.text
                    )

                    result = store_raw_opportunity(
                        source_id=source.id,
                        fetch_run_id=fetch_run.id,
                        source_reference=(
                            opportunity.source_reference
                        ),
                        source_url=str(response.url),
                        title_hint=title_hint,
                        raw_content=response.text,
                        raw_format="html",
                        source_status=source_status,
                        metadata={
                            "connector": "flextender",
                            "original_url": (
                                opportunity.source_url
                            ),
                            "final_url": str(
                                response.url
                            ),
                            "http_status": (
                                response.status_code
                            ),
                        },
                    )

                    action_counts[result.action] += 1

                except Exception as exc:
                    action_counts["failed"] += 1

                    errors.append(
                        "Opdracht "
                        f"{opportunity.source_reference} "
                        f"mislukt: {exc}"
                    )

        successful_items = (
            action_counts["created"]
            + action_counts["changed"]
            + action_counts["unchanged"]
        )

        if action_counts["failed"] == 0:
            run_status = "succeeded"
        elif successful_items > 0:
            run_status = "partial"
        else:
            run_status = "failed"

        completed_run = finish_fetch_run(
            fetch_run_id=fetch_run.id,
            source_id=source.id,
            status=run_status,
            http_status=last_http_status,
            items_discovered=len(
                discovered_by_reference
            ),
            items_new=action_counts["created"],
            items_changed=action_counts["changed"],
            items_unchanged=(
                action_counts["unchanged"]
            ),
            items_failed=action_counts["failed"],
            error_message=(
                "; ".join(errors[:5])
                if errors
                else None
            ),
            metadata={
                "connector": "flextender",
                "discovery_results": (
                    discovery_results
                ),
                "selected_items": min(
                    selected_limit,
                    len(discovered_by_reference),
                ),
                "errors": errors,
            },
        )

        return FlextenderRunSummary(
            fetch_run_id=completed_run.id,
            discovered=len(
                discovered_by_reference
            ),
            selected=min(
                selected_limit,
                len(discovered_by_reference),
            ),
            created=action_counts["created"],
            changed=action_counts["changed"],
            unchanged=action_counts["unchanged"],
            failed=action_counts["failed"],
            errors=tuple(errors),
        )

    except Exception as exc:
        try:
            finish_fetch_run(
                fetch_run_id=fetch_run.id,
                source_id=source.id,
                status="failed",
                http_status=last_http_status,
                items_discovered=len(
                    discovered_by_reference
                ),
                items_new=action_counts["created"],
                items_changed=(
                    action_counts["changed"]
                ),
                items_unchanged=(
                    action_counts["unchanged"]
                ),
                items_failed=(
                    action_counts["failed"]
                ),
                error_message=str(exc),
                metadata={
                    "connector": "flextender",
                    "discovery_results": (
                        discovery_results
                    ),
                    "errors": errors,
                },
            )
        except Exception:
            # De oorspronkelijke fout blijft leidend.
            pass

        raise