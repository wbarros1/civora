"""Uitvoering van de eerste Flextender-connector."""

from collections import Counter
from dataclasses import dataclass
from typing import Any
from uuid import UUID


from backend.app.connectors.flextender.client import (
    FlextenderHttpClient,
)
from backend.app.connectors.flextender.parser import (
    detect_source_status,
    parse_title_hint,
    validate_detail_page,
    build_detail_url,
    parse_listing_references,
    parse_search_result_html,
    parse_widget_config,
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

FLEXTENDER_LISTING_URL = (
    "https://www.flextender.nl/opdrachten/"
)

FLEXTENDER_AJAX_URL = (
    "https://www.flextender.nl/wp-admin/admin-ajax.php"
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

def discover_flextender_opportunities(
    client: FlextenderHttpClient,
) -> list[tuple[str, str]]:
    """
    Ontdek alle Flextender-opdrachten via de openbare AJAX-call.

    Retourneert tuples:
    - source_reference;
    - detail-URL.
    """

    listing_response = client.get_html(
        FLEXTENDER_LISTING_URL
    )

    widget_config = parse_widget_config(
        listing_response.text
    )

    ajax_data = client.post_search_jobs(
        ajax_url=FLEXTENDER_AJAX_URL,
        widget_config=widget_config,
    )

    result_html = parse_search_result_html(
        ajax_data
    )

    source_references = parse_listing_references(
        result_html
    )

    if not source_references:
        raise RuntimeError(
            "De Flextender AJAX-call bevatte geen "
            "opdrachtreferenties."
        )

    return [
        (
            source_reference,
            build_detail_url(
                source_reference
            ),
        )
        for source_reference in source_references
    ]

def run_flextender_connector(
    *,
    max_items: int | None = None,
) -> FlextenderRunSummary:
    """Haal openbare Flextender-opdrachten op via de AJAX-discovery."""

    settings = get_settings()
    source = get_source_by_code(
        "flextender"
    )

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

    request_delay = float(
        source.configuration.get(
            "request_delay_seconds",
            settings.scraper_request_delay_seconds,
        )
    )

    fetch_run = create_fetch_run(
        source_id=source.id,
        triggered_by="manual",
        request_url=FLEXTENDER_LISTING_URL,
        metadata={
            "connector": "flextender",
            "discovery_method": "wordpress_ajax",
            "listing_url": FLEXTENDER_LISTING_URL,
            "ajax_url": FLEXTENDER_AJAX_URL,
            "max_items": selected_limit,
        },
    )

    discovered_opportunities: list[
        tuple[str, str]
    ] = []

    selected_opportunities: list[
        tuple[str, str]
    ] = []

    discovery_results: list[
        dict[str, Any]
    ] = []

    action_counts: Counter[str] = (
        Counter()
    )

    errors: list[str] = []

    last_http_status: int | None = None

    try:
        with FlextenderHttpClient(
            user_agent=settings.user_agent,
            timeout_seconds=(
                settings.request_timeout_seconds
            ),
        ) as http_client:
            try:
                discovered_opportunities = (
                    discover_flextender_opportunities(
                        http_client
                    )
                )

                last_http_status = 200

                discovery_results.append(
                    {
                        "method": "wordpress_ajax",
                        "listing_url": (
                            FLEXTENDER_LISTING_URL
                        ),
                        "ajax_url": (
                            FLEXTENDER_AJAX_URL
                        ),
                        "http_status": 200,
                        "found": len(
                            discovered_opportunities
                        ),
                    }
                )

            except Exception as exc:
                error_message = (
                    "Flextender AJAX-discovery "
                    f"mislukt: {exc}"
                )

                errors.append(
                    error_message
                )

                discovery_results.append(
                    {
                        "method": "wordpress_ajax",
                        "listing_url": (
                            FLEXTENDER_LISTING_URL
                        ),
                        "ajax_url": (
                            FLEXTENDER_AJAX_URL
                        ),
                        "error": str(exc),
                        "found": 0,
                    }
                )

                raise RuntimeError(
                    error_message
                ) from exc

            if not discovered_opportunities:
                raise RuntimeError(
                    "De Flextender AJAX-call "
                    "heeft geen opdrachten opgeleverd."
                )

            selected_opportunities = (
                discovered_opportunities[
                    :selected_limit
                ]
            )

            for (
                source_reference,
                source_url,
            ) in selected_opportunities:
                try:
                    response = (
                        http_client.get_html(
                            source_url,
                            delay_seconds=(
                                request_delay
                            ),
                        )
                    )

                    last_http_status = (
                        response.status_code
                    )

                    validate_detail_page(
                        page_html=response.text,
                        source_reference=(
                            source_reference
                        ),
                    )

                    title_hint = (
                        parse_title_hint(
                            response.text
                        )
                    )

                    source_status = (
                        detect_source_status(
                            response.text
                        )
                    )

                    result = (
                        store_raw_opportunity(
                            source_id=source.id,
                            fetch_run_id=(
                                fetch_run.id
                            ),
                            source_reference=(
                                source_reference
                            ),
                            source_url=str(
                                response.url
                            ),
                            title_hint=(
                                title_hint
                            ),
                            raw_content=(
                                response.text
                            ),
                            raw_format="html",
                            source_status=(
                                source_status
                            ),
                            metadata={
                                "connector": (
                                    "flextender"
                                ),
                                "discovery_method": (
                                    "wordpress_ajax"
                                ),
                                "original_url": (
                                    source_url
                                ),
                                "final_url": str(
                                    response.url
                                ),
                                "http_status": (
                                    response.status_code
                                ),
                            },
                        )
                    )

                    action_counts[
                        result.action
                    ] += 1

                except Exception as exc:
                    action_counts[
                        "failed"
                    ] += 1

                    errors.append(
                        "Opdracht "
                        f"{source_reference} "
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
                discovered_opportunities
            ),
            items_new=(
                action_counts["created"]
            ),
            items_changed=(
                action_counts["changed"]
            ),
            items_unchanged=(
                action_counts["unchanged"]
            ),
            items_failed=(
                action_counts["failed"]
            ),
            error_message=(
                "; ".join(errors[:5])
                if errors
                else None
            ),
            metadata={
                "connector": "flextender",
                "discovery_method": (
                    "wordpress_ajax"
                ),
                "discovery_results": (
                    discovery_results
                ),
                "selected_items": len(
                    selected_opportunities
                ),
                "errors": errors,
            },
        )

        return FlextenderRunSummary(
            fetch_run_id=(
                completed_run.id
            ),
            discovered=len(
                discovered_opportunities
            ),
            selected=len(
                selected_opportunities
            ),
            created=(
                action_counts["created"]
            ),
            changed=(
                action_counts["changed"]
            ),
            unchanged=(
                action_counts["unchanged"]
            ),
            failed=(
                action_counts["failed"]
            ),
            errors=tuple(
                errors
            ),
        )

    except Exception as exc:
        try:
            finish_fetch_run(
                fetch_run_id=fetch_run.id,
                source_id=source.id,
                status="failed",
                http_status=last_http_status,
                items_discovered=len(
                    discovered_opportunities
                ),
                items_new=(
                    action_counts["created"]
                ),
                items_changed=(
                    action_counts["changed"]
                ),
                items_unchanged=(
                    action_counts["unchanged"]
                ),
                items_failed=(
                    action_counts["failed"]
                ),
                error_message=str(
                    exc
                ),
                metadata={
                    "connector": (
                        "flextender"
                    ),
                    "discovery_method": (
                        "wordpress_ajax"
                    ),
                    "discovery_results": (
                        discovery_results
                    ),
                    "selected_items": len(
                        selected_opportunities
                    ),
                    "errors": errors,
                },
            )

        except Exception:
            # De oorspronkelijke fout blijft leidend.
            pass

        raise    