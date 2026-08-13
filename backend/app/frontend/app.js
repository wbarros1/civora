const API_BASE = "/api/v1";
const PAGE_SIZE = 12;

const state = {
    offset: 0,
    hasMore: false,
    loading: false,
};


const elements = {
    form: document.getElementById(
        "filter-form"
    ),
    grid: document.getElementById(
        "opportunity-grid"
    ),
    loading: document.getElementById(
        "loading-state"
    ),
    empty: document.getElementById(
        "empty-state"
    ),
    error: document.getElementById(
        "error-message"
    ),
    resultsMeta: document.getElementById(
        "results-meta"
    ),
    loadMoreContainer:
        document.getElementById(
            "load-more-container"
        ),
    loadMore:
        document.getElementById(
            "load-more"
        ),
    reset:
        document.getElementById(
            "reset-filters"
        ),
    drawer:
        document.getElementById(
            "detail-drawer"
        ),
    backdrop:
        document.getElementById(
            "drawer-backdrop"
        ),
    closeDrawer:
        document.getElementById(
            "close-drawer"
        ),
    drawerContent:
        document.getElementById(
            "drawer-content"
        ),
};


function escapeHtml(value) {
    if (
        value === null
        || value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatDate(value) {
    if (!value) {
        return "Niet vermeld";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat(
        "nl-NL",
        {
            day: "numeric",
            month: "short",
            year: "numeric",
        }
    ).format(date);
}


function formatHours(
    minimum,
    maximum
) {
    if (
        minimum === null
        && maximum === null
    ) {
        return "Uren niet vermeld";
    }

    if (
        minimum !== null
        && maximum !== null
        && Number(minimum) === Number(maximum)
    ) {
        return `${minimum} uur`;
    }

    if (
        minimum !== null
        && maximum !== null
    ) {
        return `${minimum} - ${maximum} uur`;
    }

    if (maximum !== null) {
        return `Max. ${maximum} uur`;
    }

    return `Vanaf ${minimum} uur`;
}


function formatRate(item) {
    const minimum = item.rate_min;
    const maximum = item.rate_max;

    if (
        minimum === null
        && maximum === null
    ) {
        return "Tarief niet vermeld";
    }

    const currency =
        item.rate_currency === "EUR"
            ? "€"
            : (
                item.rate_currency || ""
            );

    const suffix =
        item.rate_period === "hour"
            ? " / uur"
            : "";

    if (
        minimum !== null
        && maximum !== null
        && Number(minimum) !== Number(maximum)
    ) {
        return (
            `${currency}${minimum} - `
            + `${currency}${maximum}`
            + suffix
        );
    }

    const value =
        maximum !== null
            ? maximum
            : minimum;

    return `${currency}${value}${suffix}`;
}


function formatWorkArrangement(value) {
    const mapping = {
        hybrid: "Hybride",
        on_site: "Op locatie",
        remote: "Remote",
        unknown: "Werkvorm onbekend",
    };

    return mapping[value]
        || "Werkvorm onbekend";
}


function formatRelationship(value) {
    const mapping = {
        zzp: "ZZP",
        secondment: "Detachering",
        both: "ZZP / detachering",
        unknown: "Niet vermeld",
    };

    return mapping[value]
        || "Niet vermeld";
}


function getLocation(item) {
    return (
        item.location
        || item.province
        || "Locatie niet vermeld"
    );
}


function createCard(item) {
    const article =
        document.createElement(
            "article"
        );

    article.className =
        "opportunity-card";

    article.tabIndex = 0;

    article.innerHTML = `
        <div class="card-top">
            <span class="card-reference">
                REF. ${escapeHtml(
                    item.source_reference
                )}
            </span>

            <span class="badge">
                ${escapeHtml(
                    formatWorkArrangement(
                        item.work_arrangement
                    )
                )}
            </span>
        </div>

        <h3>
            ${escapeHtml(item.title)}
        </h3>

        <p class="card-client">
            ${escapeHtml(
                item.client_name
                || "Opdrachtgever niet vermeld"
            )}
        </p>

        <div class="card-details">

            <div class="card-detail">
                <span class="detail-dot"></span>
                ${escapeHtml(
                    getLocation(item)
                )}
            </div>

            <div class="card-detail">
                <span class="detail-dot"></span>
                ${escapeHtml(
                    formatHours(
                        item.hours_per_week_min,
                        item.hours_per_week_max
                    )
                )}
            </div>

            <div class="card-detail">
                <span class="detail-dot"></span>
                ${escapeHtml(
                    formatRate(item)
                )}
            </div>

            <div class="card-detail">
                <span class="detail-dot"></span>
                ${escapeHtml(
                    formatRelationship(
                        item.employment_relationship
                    )
                )}
            </div>

        </div>

        <div class="card-footer">
            <div class="deadline">
                Reageren vóór
                <strong>
                    ${escapeHtml(
                        formatDate(
                            item.application_deadline
                        )
                    )}
                </strong>
            </div>

            <span class="card-link">
                Bekijk
                <span>→</span>
            </span>
        </div>
    `;

    article.addEventListener(
        "click",
        () => {
            openOpportunity(
                item.id
            );
        }
    );

    article.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Enter"
                || event.key === " "
            ) {
                event.preventDefault();

                openOpportunity(
                    item.id
                );
            }
        }
    );

    return article;
}


function getFilters() {
    const formData =
        new FormData(
            elements.form
        );

    const params =
        new URLSearchParams();

    for (
        const [key, rawValue]
        of formData.entries()
    ) {
        const value =
            String(rawValue).trim();

        if (value) {
            params.set(
                key,
                value
            );
        }
    }

    return params;
}


async function loadOpportunities({
    append = false,
} = {}) {
    if (state.loading) {
        return;
    }

    state.loading = true;
    elements.error.classList.add(
        "hidden"
    );

    if (!append) {
        state.offset = 0;

        elements.grid.innerHTML = "";
        elements.grid.classList.add(
            "hidden"
        );

        elements.loading.classList.remove(
            "hidden"
        );

        elements.empty.classList.add(
            "hidden"
        );
    }

    const params = getFilters();

    params.set(
        "limit",
        PAGE_SIZE
    );

    params.set(
        "offset",
        state.offset
    );

    try {
        const response = await fetch(
            `${API_BASE}/opportunities?${params}`
        );

        if (!response.ok) {
            throw new Error(
                "Opdrachten konden niet worden geladen."
            );
        }

        const data =
            await response.json();

        if (!append) {
            elements.grid.innerHTML = "";
        }

        for (
            const item
            of data.items
        ) {
            elements.grid.appendChild(
                createCard(item)
            );
        }

        state.hasMore =
            Boolean(
                data.has_more
            );

        state.offset +=
            data.items.length;

        elements.loading.classList.add(
            "hidden"
        );

        if (
            state.offset === 0
        ) {
            elements.grid.classList.add(
                "hidden"
            );

            elements.empty.classList.remove(
                "hidden"
            );
        } else {
            elements.empty.classList.add(
                "hidden"
            );

            elements.grid.classList.remove(
                "hidden"
            );
        }

        elements.resultsMeta.textContent =
            state.offset === 1
                ? "1 opdracht geladen"
                : `${state.offset} opdrachten geladen`;

        elements.loadMoreContainer
            .classList.toggle(
                "hidden",
                !state.hasMore
            );

    } catch (error) {
        console.error(error);

        elements.loading.classList.add(
            "hidden"
        );

        elements.error.textContent =
            "Er ging iets mis bij het laden "
            + "van de opdrachten.";

        elements.error.classList.remove(
            "hidden"
        );

    } finally {
        state.loading = false;
    }
}


function renderList(
    title,
    values
) {
    if (
        !Array.isArray(values)
        || values.length === 0
    ) {
        return "";
    }

    return `
        <section class="drawer-section">
            <h3>
                ${escapeHtml(title)}
            </h3>

            <ul class="drawer-list">
                ${values.map(
                    (value) => `
                        <li>
                            ${escapeHtml(value)}
                        </li>
                    `
                ).join("")}
            </ul>
        </section>
    `;
}


function renderDescription(
    value
) {
    if (!value) {
        return "";
    }

    const paragraphs =
        String(value)
            .split(/\n+/)
            .map(
                (paragraph) =>
                    paragraph.trim()
            )
            .filter(Boolean);

    return `
        <section class="drawer-section">
            <h3>Over de opdracht</h3>

            ${paragraphs.map(
                (paragraph) => `
                    <p>
                        ${escapeHtml(paragraph)}
                    </p>
                `
            ).join("<br>")}
        </section>
    `;
}


async function openOpportunity(id) {
    elements.drawerContent.innerHTML = `
        <p>
            Opdracht laden...
        </p>
    `;

    elements.drawer.classList.add(
        "open"
    );

    elements.drawer.setAttribute(
        "aria-hidden",
        "false"
    );

    elements.backdrop.classList.remove(
        "hidden"
    );

    document.body.classList.add(
        "drawer-open"
    );

    try {
        const response = await fetch(
            `${API_BASE}/opportunities/${id}`
        );

        if (!response.ok) {
            throw new Error(
                "Detail kon niet worden geladen."
            );
        }

        const item =
            await response.json();

        elements.drawerContent.innerHTML = `
            <span class="drawer-eyebrow">
                PUBLIEKE INHUUROPDRACHT
                · REF.
                ${escapeHtml(
                    item.source_reference
                )}
            </span>

            <h2 class="drawer-title">
                ${escapeHtml(item.title)}
            </h2>

            <p class="drawer-client">
                ${escapeHtml(
                    item.client_name
                    || "Opdrachtgever niet vermeld"
                )}
            </p>

            <div class="drawer-summary">

                <div class="summary-item">
                    <span class="summary-label">
                        Locatie
                    </span>

                    <span class="summary-value">
                        ${escapeHtml(
                            getLocation(item)
                        )}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Werkvorm
                    </span>

                    <span class="summary-value">
                        ${escapeHtml(
                            formatWorkArrangement(
                                item.work_arrangement
                            )
                        )}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Uren
                    </span>

                    <span class="summary-value">
                        ${escapeHtml(
                            formatHours(
                                item.hours_per_week_min,
                                item.hours_per_week_max
                            )
                        )}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Tarief
                    </span>

                    <span class="summary-value">
                        ${escapeHtml(
                            formatRate(item)
                        )}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Contract
                    </span>

                    <span class="summary-value">
                        ${escapeHtml(
                            formatRelationship(
                                item.employment_relationship
                            )
                        )}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Deadline
                    </span>

                    <span class="summary-value">
                        ${escapeHtml(
                            formatDate(
                                item.application_deadline
                            )
                        )}
                    </span>
                </div>

            </div>

            ${renderDescription(
                item.description
            )}

            ${renderList(
                "Eisen",
                item.requirements
            )}

            ${renderList(
                "Wensen",
                item.wishes
            )}

            ${renderList(
                "Competenties",
                item.competencies
            )}

            ${renderList(
                "Vaardigheden",
                item.skills
            )}

            <section class="drawer-section">
                <h3>
                    Planning
                </h3>

                <div class="drawer-summary">

                    <div class="summary-item">
                        <span class="summary-label">
                            Start
                        </span>

                        <span class="summary-value">
                            ${escapeHtml(
                                formatDate(
                                    item.start_date
                                )
                            )}
                        </span>
                    </div>

                    <div class="summary-item">
                        <span class="summary-label">
                            Einde
                        </span>

                        <span class="summary-value">
                            ${escapeHtml(
                                formatDate(
                                    item.end_date
                                )
                            )}
                        </span>
                    </div>

                </div>
            </section>
        `;

    } catch (error) {
        console.error(error);

        elements.drawerContent.innerHTML = `
            <div class="message message-error">
                De opdracht kon niet worden geladen.
            </div>
        `;
    }
}


function closeDrawer() {
    elements.drawer.classList.remove(
        "open"
    );

    elements.drawer.setAttribute(
        "aria-hidden",
        "true"
    );

    elements.backdrop.classList.add(
        "hidden"
    );

    document.body.classList.remove(
        "drawer-open"
    );
}


elements.form.addEventListener(
    "submit",
    (event) => {
        event.preventDefault();

        loadOpportunities();
    }
);


elements.reset.addEventListener(
    "click",
    () => {
        elements.form.reset();

        loadOpportunities();
    }
);


elements.loadMore.addEventListener(
    "click",
    () => {
        loadOpportunities({
            append: true,
        });
    }
);


elements.closeDrawer.addEventListener(
    "click",
    closeDrawer
);


elements.backdrop.addEventListener(
    "click",
    closeDrawer
);


document.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key === "Escape"
        ) {
            closeDrawer();
        }
    }
);


loadOpportunities();