const {
    supabaseUrl,
    supabasePublishableKey,
} = window.CIVORA_CONFIG;


const supabaseClient =
    window.supabase.createClient(
        supabaseUrl,
        supabasePublishableKey,
        {
            auth: {
                persistSession: true,
                autoRefreshToken: true,
                detectSessionInUrl: true,
            },
        }
    );


let currentSession = null;
let currentUser = null;


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
    
    authScreen:
    document.getElementById(
        "auth-screen"
    ),

    appShell:
        document.getElementById(
            "app-shell"
        ),

    loginForm:
        document.getElementById(
            "login-form"
        ),

    registerForm:
        document.getElementById(
            "register-form"
        ),

    showLogin:
        document.getElementById(
            "show-login"
        ),

    showRegister:
        document.getElementById(
            "show-register"
        ),

    authMessage:
        document.getElementById(
            "auth-message"
        ),

    logoutButton:
        document.getElementById(
            "logout-button"
        ),

    userName:
        document.getElementById(
            "user-name"
        ),

    userVakgroep:
        document.getElementById(
            "user-vakgroep"
        ),

    userInitials:
        document.getElementById(
            "user-initials"
        ),

    profileButton:
    document.getElementById(
        "profile-button"
    ),

    profileModal:
        document.getElementById(
            "profile-modal"
        ),

    profileBackdrop:
        document.getElementById(
            "profile-backdrop"
        ),

    closeProfile:
        document.getElementById(
            "close-profile"
        ),

    cancelProfile:
        document.getElementById(
            "cancel-profile"
        ),

    profileForm:
        document.getElementById(
            "profile-form"
        ),

    profileName:
        document.getElementById(
            "profile-name"
        ),

    profileEmail:
        document.getElementById(
            "profile-email"
        ),

    profileVakgroep:
        document.getElementById(
            "profile-vakgroep"
        ),

    profileRole:
        document.getElementById(
            "profile-role"
        ),

    profileMessage:
        document.getElementById(
            "profile-message"
        ),
    
    saveSearchButton:
    document.getElementById(
        "save-search-button"
    ),

    showSavedSearches:
        document.getElementById(
            "show-saved-searches"
        ),

    saveSearchModal:
        document.getElementById(
            "save-search-modal"
        ),

    saveSearchBackdrop:
        document.getElementById(
            "save-search-backdrop"
        ),

    closeSaveSearch:
        document.getElementById(
            "close-save-search"
        ),

    cancelSaveSearch:
        document.getElementById(
            "cancel-save-search"
        ),

    saveSearchForm:
        document.getElementById(
            "save-search-form"
        ),

    savedSearchName:
        document.getElementById(
            "saved-search-name"
        ),

    saveSearchMessage:
        document.getElementById(
            "save-search-message"
        ),

    saveSearchPreview:
        document.getElementById(
            "save-search-preview"
        ),

    savedSearchesModal:
        document.getElementById(
            "saved-searches-modal"
        ),

    savedSearchesBackdrop:
        document.getElementById(
            "saved-searches-backdrop"
        ),

    closeSavedSearches:
        document.getElementById(
            "close-saved-searches"
        ),

    savedSearchesList:
        document.getElementById(
            "saved-searches-list"
        ),

    savedSearchesMessage:
        document.getElementById(
            "saved-searches-message"
        ),
};

function showAuthMessage(
    message,
    type = "error"
) {
    elements.authMessage.textContent =
        message;

    elements.authMessage.className =
        `auth-message ${type}`;
}


function clearAuthMessage() {
    elements.authMessage.textContent =
        "";

    elements.authMessage.className =
        "auth-message hidden";
}


function formatVakgroep(value) {
    const mapping = {
        procesmanagement:
            "Procesmanagement",

        data_ai:
            "Data & AI",

        ict:
            "ICT",

        finance:
            "Finance",
    };

    return mapping[value] || value;
}


function getInitials(name) {
    return String(name)
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map(
            part =>
                part
                    .charAt(0)
                    .toUpperCase()
        )
        .join("");
}


async function apiFetch(
    path,
    options = {}
) {
    const {
        data,
        error,
    } = await supabaseClient
        .auth
        .getSession();

    if (error) {
        console.error(
            "Supabase sessie kon niet worden opgehaald:",
            error
        );

        throw new Error(
            "Je sessie kon niet worden gecontroleerd."
        );
    }

    const session =
        data.session;

    currentSession =
        session;

    const headers =
        new Headers(
            options.headers || {}
        );

    if (session?.access_token) {
        headers.set(
            "Authorization",
            `Bearer ${session.access_token}`
        );
    }

    return fetch(
        `${API_BASE}${path}`,
        {
            ...options,
            headers,
        }
    );
}

function renderCurrentUser() {
    if (!currentUser) {
        return;
    }

    elements.userName.textContent =
        currentUser.full_name;

    elements.userVakgroep.textContent =
        formatVakgroep(
            currentUser.vakgroep
        );

    elements.userInitials.textContent =
        getInitials(
            currentUser.full_name
        );
}

async function loadCurrentUser() {
    const response =
        await apiFetch(
            "/auth/me"
        );

    if (!response.ok) {
        throw new Error(
            "Gebruikersprofiel kon "
            + "niet worden geladen."
        );
    }

    currentUser =
        await response.json();

    renderCurrentUser();
}

function openProfile() {
    if (!currentUser) {
        return;
    }

    elements.profileName.value =
        currentUser.full_name;

    elements.profileEmail.textContent =
        currentUser.email
        || "Niet beschikbaar";

    elements.profileVakgroep.value =
        currentUser.vakgroep;

    elements.profileRole.textContent =
        currentUser.role === "admin"
            ? "Administrator"
            : "Gebruiker";

    elements.profileMessage
        .classList
        .add(
            "hidden"
        );

    elements.profileModal
        .classList
        .remove(
            "hidden"
        );

    elements.profileBackdrop
        .classList
        .remove(
            "hidden"
        );

    document.body.classList.add(
        "drawer-open"
    );
}


function closeProfile() {
    elements.profileModal
        .classList
        .add(
            "hidden"
        );

    elements.profileBackdrop
        .classList
        .add(
            "hidden"
        );

    document.body.classList.remove(
        "drawer-open"
    );
}

elements.profileForm.addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const fullName =
            elements
                .profileName
                .value
                .trim();

        const vakgroep =
            elements
                .profileVakgroep
                .value;

        elements.profileMessage
            .classList
            .add(
                "hidden"
            );

        try {
            const response =
                await apiFetch(
                    "/auth/me",
                    {
                        method: "PATCH",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    full_name:
                                        fullName,

                                    vakgroep:
                                        vakgroep,
                                }
                            ),
                    }
                );

            if (!response.ok) {
                const errorData =
                    await response
                        .json()
                        .catch(
                            () => ({})
                        );

                throw new Error(
                    errorData.detail
                    || "Profiel kon niet worden opgeslagen."
                );
            }

            currentUser =
                await response.json();

            renderCurrentUser();

            elements.profileMessage
                .textContent =
                    "Je profiel is bijgewerkt.";

            elements.profileMessage
                .className =
                    "auth-message success";

        } catch (error) {
            console.error(error);

            elements.profileMessage
                .textContent =
                    error.message
                    || (
                        "Profiel kon niet "
                        + "worden opgeslagen."
                    );

            elements.profileMessage
                .className =
                    "auth-message error";
        }
    }
);

elements.profileButton.addEventListener(
    "click",
    openProfile
);


elements.closeProfile.addEventListener(
    "click",
    closeProfile
);


elements.cancelProfile.addEventListener(
    "click",
    closeProfile
);


elements.profileBackdrop.addEventListener(
    "click",
    closeProfile
);

elements.loginForm.addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        clearAuthMessage();

        const email =
            document
                .getElementById(
                    "login-email"
                )
                .value
                .trim();

        const password =
            document
                .getElementById(
                    "login-password"
                )
                .value;

        const {
            data,
            error,
        } = await supabaseClient
            .auth
            .signInWithPassword({
                email,
                password,
            });

        if (error) {
            showAuthMessage(
                "Inloggen is niet gelukt. "
                + "Controleer je gegevens."
            );

            return;
        }

        currentSession =
            data.session;

        await showAuthenticatedApp();
    }
);

elements.registerForm.addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        clearAuthMessage();

        const fullName =
            document
                .getElementById(
                    "register-name"
                )
                .value
                .trim();

        const email =
            document
                .getElementById(
                    "register-email"
                )
                .value
                .trim();

        const password =
            document
                .getElementById(
                    "register-password"
                )
                .value;

        const vakgroep =
            document
                .getElementById(
                    "register-vakgroep"
                )
                .value;

        const {
            data,
            error,
        } = await supabaseClient
            .auth
            .signUp({
                email,
                password,

                options: {
                    data: {
                        full_name:
                            fullName,

                        vakgroep:
                            vakgroep,
                    },
                },
            });

        if (error) {
            showAuthMessage(
                error.message
            );

            return;
        }

        if (!data.session) {
            showAuthMessage(
                "Account aangemaakt. "
                + "Controleer je e-mail "
                + "om je account te bevestigen.",
                "success"
            );

            return;
        }

        currentSession =
            data.session;

        await showAuthenticatedApp();
    }
);

async function showAuthenticatedApp() {
    try {
        await loadCurrentUser();

        elements.authScreen.classList.add(
            "hidden"
        );

        elements.appShell.classList.remove(
            "hidden"
        );

        await loadOpportunities();

    } catch (error) {
        console.error(
            "Initialisatie van Civora mislukt:",
            error
        );

        elements.appShell.classList.add(
            "hidden"
        );

        elements.authScreen.classList.remove(
            "hidden"
        );

        showAuthMessage(
            "Je sessie is actief, maar je profiel "
            + "kon niet worden geladen. "
            + "Ververs de pagina of probeer het opnieuw."
        );
    }
}

elements.showLogin.addEventListener(
    "click",
    () => {
        clearAuthMessage();

        elements.loginForm
            .classList
            .remove(
                "hidden"
            );

        elements.registerForm
            .classList
            .add(
                "hidden"
            );

        elements.showLogin
            .classList
            .add(
                "active"
            );

        elements.showRegister
            .classList
            .remove(
                "active"
            );
    }
);


elements.showRegister.addEventListener(
    "click",
    () => {
        clearAuthMessage();

        elements.loginForm
            .classList
            .add(
                "hidden"
            );

        elements.registerForm
            .classList
            .remove(
                "hidden"
            );

        elements.showLogin
            .classList
            .remove(
                "active"
            );

        elements.showRegister
            .classList
            .add(
                "active"
            );
    }
);


elements.logoutButton.addEventListener(
    "click",
    async () => {
        await supabaseClient
            .auth
            .signOut();

        currentSession = null;
        currentUser = null;

        elements.appShell.classList.add(
            "hidden"
        );

        elements.authScreen.classList.remove(
            "hidden"
        );
    }
);

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

function getFiltersObject() {
    const params =
        getFilters();

    return Object.fromEntries(
        params.entries()
    );
}

function formatFilterValue(
    key,
    value
) {
    if (
        key === "work_arrangement"
    ) {
        return formatWorkArrangement(
            value
        );
    }

    if (
        key === "employment_relationship"
    ) {
        return formatRelationship(
            value
        );
    }

    if (
        key === "application_status"
    ) {
        const mapping = {
            open: "Open",
            closed: "Gesloten",
            unknown: "Onbekend",
        };

        return mapping[value] || value;
    }

    return value;
}

function openSaveSearchModal() {
    const filters =
        getFiltersObject();

    elements.savedSearchName.value =
        "";

    elements.saveSearchMessage
        .classList
        .add(
            "hidden"
        );

    const entries =
        Object.entries(
            filters
        );

    if (entries.length === 0) {
        elements.saveSearchPreview.innerHTML = `
            <span>
                Geen filters geselecteerd.
            </span>
        `;
    } else {
        elements.saveSearchPreview.innerHTML =
            entries.map(
                ([key, value]) => `
                    <div
                        class="saved-search-preview-row"
                    >
                        <span>
                            ${escapeHtml(
                                formatFilterName(
                                    key
                                )
                            )}
                        </span>

                        <strong>
                            ${escapeHtml(
                                formatFilterValue(
                                    key,
                                    value
                                )
                            )}
                        </strong>
                    </div>
                `
            ).join("");
    }

    elements.saveSearchModal
        .classList
        .remove(
            "hidden"
        );

    elements.saveSearchBackdrop
        .classList
        .remove(
            "hidden"
        );

    document.body.classList.add(
        "drawer-open"
    );

    setTimeout(
        () => {
            elements
                .savedSearchName
                .focus();
        },
        0
    );
}


function closeSaveSearchModal() {
    elements.saveSearchModal
        .classList
        .add(
            "hidden"
        );

    elements.saveSearchBackdrop
        .classList
        .add(
            "hidden"
        );

    document.body.classList.remove(
        "drawer-open"
    );
}


elements.saveSearchForm.addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const name =
            elements
                .savedSearchName
                .value
                .trim();

        if (!name) {
            return;
        }

        const filters =
            getFiltersObject();

        elements.saveSearchMessage
            .classList
            .add(
                "hidden"
            );

        try {
            const response =
                await apiFetch(
                    "/saved-searches",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    name,
                                    filters,
                                }
                            ),
                    }
                );

            if (!response.ok) {
                const errorData =
                    await response
                        .json()
                        .catch(
                            () => ({})
                        );

                throw new Error(
                    errorData.detail
                    || (
                        "Zoekopdracht kon "
                        + "niet worden opgeslagen."
                    )
                );
            }

            elements.saveSearchMessage
                .textContent =
                    "Zoekopdracht opgeslagen.";

            elements.saveSearchMessage
                .className =
                    "auth-message success";

            setTimeout(
                closeSaveSearchModal,
                700
            );

        } catch (error) {
            console.error(error);

            elements.saveSearchMessage
                .textContent =
                    error.message;

            elements.saveSearchMessage
                .className =
                    "auth-message error";
        }
    }
);

async function loadSavedSearches() {
    elements.savedSearchesList.innerHTML =
        `
            <div class="saved-search-empty">
                Laden...
            </div>
        `;

    const response =
        await apiFetch(
            "/saved-searches"
        );

    if (!response.ok) {
        throw new Error(
            "Opgeslagen zoekopdrachten "
            + "konden niet worden geladen."
        );
    }

    return response.json();
}

function createSavedSearchTags(
    filters
) {
    const entries =
        Object.entries(
            filters || {}
        );

    if (entries.length === 0) {
        return `
            <span class="saved-search-tag">
                Geen filters
            </span>
        `;
    }

    return entries.map(
        ([key, value]) => `
            <span class="saved-search-tag">
                ${escapeHtml(
                    formatFilterName(
                        key
                    )
                )}:
                ${escapeHtml(
                    formatFilterValue(
                        key,
                        value
                    )
                )}
            </span>
        `
    ).join("");
}

async function applySavedSearch(
    savedSearch
) {
    elements.form.reset();

    const filters =
        savedSearch.filters || {};

    for (
        const [key, value]
        of Object.entries(
            filters
        )
    ) {
        const field =
            elements.form.elements[
                key
            ];

        if (field) {
            field.value =
                value;
        }
    }

    closeSavedSearchesModal();

    await loadOpportunities();

    document
        .querySelector(
            ".content-section"
        )
        ?.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
}

async function removeSavedSearch(
    savedSearchId
) {
    const response =
        await apiFetch(
            `/saved-searches/${savedSearchId}`,
            {
                method: "DELETE",
            }
        );

    if (!response.ok) {
        throw new Error(
            "Zoekopdracht kon "
            + "niet worden verwijderd."
        );
    }
}

async function openSavedSearchesModal() {
    elements.savedSearchesModal
        .classList
        .remove(
            "hidden"
        );

    elements.savedSearchesBackdrop
        .classList
        .remove(
            "hidden"
        );

    document.body.classList.add(
        "drawer-open"
    );

    elements.savedSearchesMessage
        .classList
        .add(
            "hidden"
        );

    try {
        const savedSearches =
            await loadSavedSearches();

        if (
            savedSearches.length === 0
        ) {
            elements.savedSearchesList
                .innerHTML = `
                    <div class="saved-search-empty">
                        Je hebt nog geen
                        zoekopdrachten opgeslagen.
                    </div>
                `;

            return;
        }

        elements.savedSearchesList
            .innerHTML = "";

        for (
            const savedSearch
            of savedSearches
        ) {
            const item =
                document.createElement(
                    "article"
                );

            item.className =
                "saved-search-item";

            item.innerHTML = `
                <div class="saved-search-item-header">
                    <div>
                        <h3>
                            ${escapeHtml(
                                savedSearch.name
                            )}
                        </h3>
                    </div>
                </div>

                <div class="saved-search-description">
                    ${createSavedSearchTags(
                        savedSearch.filters
                    )}
                </div>

                <div class="saved-search-actions">

                    <button
                        type="button"
                        class="
                            button
                            button-secondary
                            saved-search-delete
                        "
                    >
                        Verwijderen
                    </button>

                    <button
                        type="button"
                        class="
                            button
                            button-primary
                            saved-search-apply
                        "
                    >
                        Toepassen
                        <span>→</span>
                    </button>

                </div>
            `;

            item
                .querySelector(
                    ".saved-search-apply"
                )
                .addEventListener(
                    "click",
                    () => {
                        applySavedSearch(
                            savedSearch
                        );
                    }
                );

            item
                .querySelector(
                    ".saved-search-delete"
                )
                .addEventListener(
                    "click",
                    async () => {
                        try {
                            await removeSavedSearch(
                                savedSearch.id
                            );

                            await openSavedSearchesModal();

                        } catch (error) {
                            console.error(error);

                            elements.savedSearchesMessage
                                .textContent =
                                    error.message;

                            elements.savedSearchesMessage
                                .className =
                                    "auth-message error";
                        }
                    }
                );

            elements.savedSearchesList
                .appendChild(
                    item
                );
        }

    } catch (error) {
        console.error(error);

        elements.savedSearchesList
            .innerHTML = "";

        elements.savedSearchesMessage
            .textContent =
                error.message;

        elements.savedSearchesMessage
            .className =
                "auth-message error";
    }
}


function closeSavedSearchesModal() {
    elements.savedSearchesModal
        .classList
        .add(
            "hidden"
        );

    elements.savedSearchesBackdrop
        .classList
        .add(
            "hidden"
        );

    document.body.classList.remove(
        "drawer-open"
    );
}

elements.saveSearchButton.addEventListener(
    "click",
    openSaveSearchModal
);


elements.showSavedSearches.addEventListener(
    "click",
    openSavedSearchesModal
);


elements.closeSaveSearch.addEventListener(
    "click",
    closeSaveSearchModal
);


elements.cancelSaveSearch.addEventListener(
    "click",
    closeSaveSearchModal
);


elements.saveSearchBackdrop.addEventListener(
    "click",
    closeSaveSearchModal
);


elements.closeSavedSearches.addEventListener(
    "click",
    closeSavedSearchesModal
);


elements.savedSearchesBackdrop.addEventListener(
    "click",
    closeSavedSearchesModal
);

function formatFilterName(key) {
    const mapping = {
        search: "Zoekterm",
        client: "Opdrachtgever",
        province: "Provincie",
        work_arrangement: "Werkvorm",
        employment_relationship:
            "Contractvorm",
        application_status:
            "Reactiestatus",
    };

    return mapping[key] || key;
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
        const response = await apiFetch(
            `/opportunities?${params}`
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
        const response = await apiFetch(
            `/opportunities/${id}`
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
            closeProfile();
            closeSaveSearchModal();
            closeSavedSearchesModal();
        }
    }
);


async function initializeAuth() {
    const {
        data,
        error,
    } = await supabaseClient
        .auth
        .getSession();

    if (error) {
        console.error(error);
    }

    currentSession =
        data.session;

    if (currentSession) {
        await showAuthenticatedApp();

        return;
    }

    elements.authScreen.classList.remove(
        "hidden"
    );

    elements.appShell.classList.add(
        "hidden"
    );
}


supabaseClient
    .auth
    .onAuthStateChange(
        (
            event,
            session
        ) => {
            currentSession =
                session;

            if (
                event === "SIGNED_OUT"
            ) {
                currentUser = null;

                elements.appShell
                    .classList
                    .add(
                        "hidden"
                    );

                elements.authScreen
                    .classList
                    .remove(
                        "hidden"
                    );
            }
        }
    );


initializeAuth();