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
let currentUserCv = null;

let profileCvPollTimer = null;
let profileCvPollGeneration = 0;


const API_BASE = "/api/v1";
const PAGE_SIZE = 12;

const PROFILE_CV_POLL_INTERVAL_MS =
    2_000;

const PROFILE_CV_POLL_MAX_ATTEMPTS =
    30;

const state = {
    offset: 0,
    hasMore: false,
    loading: false,
    feed: "for_you",
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

    profileCvInput:
        document.getElementById(
            "profile-cv-input"
        ),

    profileCvLoading:
        document.getElementById(
            "profile-cv-loading"
        ),

    profileCvEmpty:
        document.getElementById(
            "profile-cv-empty"
        ),

    profileCvCurrent:
        document.getElementById(
            "profile-cv-current"
        ),

    profileCvUpload:
        document.getElementById(
            "profile-cv-upload"
        ),

    profileCvFilename:
        document.getElementById(
            "profile-cv-filename"
        ),

    profileCvMeta:
        document.getElementById(
            "profile-cv-meta"
        ),

    profileCvUploadedAt:
        document.getElementById(
            "profile-cv-uploaded-at"
        ),

    profileCvDownload:
        document.getElementById(
            "profile-cv-download"
        ),

    profileCvReplace:
        document.getElementById(
            "profile-cv-replace"
        ),

    profileCvDelete:
        document.getElementById(
            "profile-cv-delete"
        ),

    profileCvMessage:
        document.getElementById(
            "profile-cv-message"
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

    feedForYou: document.getElementById(
        "feed-for-you"
    ),

    feedAll: document.getElementById(
        "feed-all"
    ),

    feedTitle: document.getElementById(
        "feed-title"
    ),

    feedDescription: document.getElementById(
        "feed-description"
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

function formatCvFileSize(
    value
) {
    const bytes =
        Number(value);

    if (
        !Number.isFinite(bytes)
        || bytes <= 0
    ) {
        return "Onbekende grootte";
    }

    if (
        bytes < 1024 * 1024
    ) {
        return (
            `${Math.max(
                1,
                Math.round(
                    bytes / 1024
                )
            )} KB`
        );
    }

    const megabytes =
        bytes
        / (
            1024 * 1024
        );

    return (
        `${megabytes.toLocaleString(
            "nl-NL",
            {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1,
            }
        )} MB`
    );
}


function formatCvType(
    mimeType
) {
    if (
        mimeType
        === "application/pdf"
    ) {
        return "PDF";
    }

    if (
        mimeType
        === (
            "application/vnd.openxmlformats-officedocument."
            + "wordprocessingml.document"
        )
    ) {
        return "DOCX";
    }

    return "Bestand";
}


function formatCvStatus(
    value
) {
    const labels = {
        uploaded:
            "Opgeslagen",

        processing:
            "Wordt verwerkt",

        ready:
            "Klaar",

        failed:
            "Verwerking mislukt",
    };

    return (
        labels[value]
        || "Onbekende status"
    );
}


function formatCvUploadedAt(
    value
) {
    if (!value) {
        return "";
    }

    const date =
        new Date(
            value
        );

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "";
    }

    return (
        "Geüpload op "
        + new Intl.DateTimeFormat(
            "nl-NL",
            {
                day: "numeric",
                month: "long",
                year: "numeric",
            }
        ).format(
            date
        )
    );
}


function clearProfileCvMessage() {
    elements.profileCvMessage
        .textContent = "";

    elements.profileCvMessage
        .className =
            "auth-message hidden";
}


function showProfileCvMessage(
    message,
    type = "error"
) {
    elements.profileCvMessage
        .textContent =
            message;

    elements.profileCvMessage
        .className =
            `auth-message ${type}`;
}


function setProfileCvBusy(
    busy
) {
    elements.profileCvUpload
        .disabled = busy;

    elements.profileCvReplace
        .disabled = busy;

    elements.profileCvDownload
        .disabled = busy;

    elements.profileCvDelete
        .disabled = busy;

    elements.profileCvInput
        .disabled = busy;
}


function isProfileCvProcessing(
    value
) {
    return (
        value === "uploaded"
        || value === "processing"
    );
}


function cancelProfileCvPolling() {
    profileCvPollGeneration += 1;

    if (
        profileCvPollTimer
        !== null
    ) {
        window.clearTimeout(
            profileCvPollTimer
        );

        profileCvPollTimer = null;
    }
}


function showCurrentProfileCvStatus(
    {
        afterUpload = false,
    } = {}
) {
    if (!currentUserCv) {
        return;
    }

    const processingStatus =
        currentUserCv
            .processing_status;

    if (
        processingStatus
        === "failed"
    ) {
        showProfileCvMessage(
            currentUserCv
                .processing_error
            || (
                "De automatische verwerking "
                + "van je basis-CV is mislukt."
            )
        );

        return;
    }

    if (
        isProfileCvProcessing(
            processingStatus
        )
    ) {
        showProfileCvMessage(
            afterUpload
                ? (
                    "Je basis-CV is opgeslagen "
                    + "en wordt verwerkt..."
                )
                : (
                    "Je basis-CV wordt "
                    + "verwerkt..."
                ),
            "success"
        );

        return;
    }

    if (
        afterUpload
        && processingStatus
            === "ready"
    ) {
        showProfileCvMessage(
            "Je basis-CV is opgeslagen "
            + "en klaar voor gebruik.",
            "success"
        );
    }
}


function startProfileCvPolling(
    {
        cvId,
    }
) {
    cancelProfileCvPolling();

    const generation =
        profileCvPollGeneration;

    let attempts = 0;

    const scheduleNextPoll =
        () => {
            if (
                generation
                !== profileCvPollGeneration
            ) {
                return;
            }

            profileCvPollTimer =
                window.setTimeout(
                    poll,
                    PROFILE_CV_POLL_INTERVAL_MS
                );
        };

    const poll =
        async () => {
            profileCvPollTimer =
                null;

            if (
                generation
                !== profileCvPollGeneration
            ) {
                return;
            }

            if (!currentSession) {
                cancelProfileCvPolling();

                return;
            }

            if (
                elements.profileModal
                    .classList
                    .contains(
                        "hidden"
                    )
            ) {
                cancelProfileCvPolling();

                return;
            }

            if (
                attempts
                >= PROFILE_CV_POLL_MAX_ATTEMPTS
            ) {
                showProfileCvMessage(
                    "Je basis-CV is opgeslagen, "
                    + "maar de verwerking duurt "
                    + "langer dan verwacht. "
                    + "Open je profiel later "
                    + "opnieuw om de status "
                    + "te controleren.",
                    "success"
                );

                return;
            }

            attempts += 1;

            try {
                const response =
                    await apiFetch(
                        "/user-cv"
                    );

                if (!response.ok) {
                    throw new Error(
                        "CV-status kon niet "
                        + "worden opgehaald."
                    );
                }

                const latestCv =
                    await response.json();

                if (
                    generation
                    !== profileCvPollGeneration
                ) {
                    return;
                }

                if (!latestCv) {
                    currentUserCv = null;

                    renderUserCv();

                    cancelProfileCvPolling();

                    return;
                }

                if (
                    latestCv.id
                    !== cvId
                ) {
                    cancelProfileCvPolling();

                    return;
                }

                currentUserCv =
                    latestCv;

                renderUserCv();

                const processingStatus =
                    currentUserCv
                        .processing_status;

                if (
                    processingStatus
                    === "ready"
                ) {
                    cancelProfileCvPolling();

                    showProfileCvMessage(
                        "Je basis-CV is klaar "
                        + "voor gebruik.",
                        "success"
                    );

                    return;
                }

                if (
                    processingStatus
                    === "failed"
                ) {
                    cancelProfileCvPolling();

                    showProfileCvMessage(
                        currentUserCv
                            .processing_error
                        || (
                            "De automatische "
                            + "verwerking van je "
                            + "basis-CV is mislukt."
                        )
                    );

                    return;
                }

                if (
                    isProfileCvProcessing(
                        processingStatus
                    )
                ) {
                    showProfileCvMessage(
                        "Je basis-CV wordt "
                        + "verwerkt...",
                        "success"
                    );

                    scheduleNextPoll();

                    return;
                }

                cancelProfileCvPolling();

            } catch (error) {
                if (
                    generation
                    !== profileCvPollGeneration
                ) {
                    return;
                }

                if (
                    attempts
                    >= (
                        PROFILE_CV_POLL_MAX_ATTEMPTS
                    )
                ) {
                    showProfileCvMessage(
                        "De actuele CV-status "
                        + "kon niet worden "
                        + "opgehaald. Open je "
                        + "profiel later opnieuw."
                    );

                    return;
                }

                scheduleNextPoll();
            }
        };

    scheduleNextPoll();
}


function syncProfileCvProcessing(
    {
        afterUpload = false,
    } = {}
) {
    cancelProfileCvPolling();

    if (!currentUserCv) {
        return;
    }

    showCurrentProfileCvStatus(
        {
            afterUpload,
        }
    );

    if (
        isProfileCvProcessing(
            currentUserCv
                .processing_status
        )
    ) {
        startProfileCvPolling(
            {
                cvId:
                    currentUserCv.id,
            }
        );
    }
}

function renderUserCv() {
    elements.profileCvLoading
        .classList
        .add(
            "hidden"
        );

    if (!currentUserCv) {
        elements.profileCvCurrent
            .classList
            .add(
                "hidden"
            );

        elements.profileCvEmpty
            .classList
            .remove(
                "hidden"
            );

        return;
    }

    elements.profileCvEmpty
        .classList
        .add(
            "hidden"
        );

    elements.profileCvCurrent
        .classList
        .remove(
            "hidden"
        );

    elements.profileCvFilename
        .textContent =
            currentUserCv
                .original_filename
            || "Basis-CV";

    elements.profileCvMeta
        .textContent = [
            formatCvType(
                currentUserCv
                    .mime_type
            ),

            formatCvFileSize(
                currentUserCv
                    .file_size_bytes
            ),

            formatCvStatus(
                currentUserCv
                    .processing_status
            ),
        ].join(
            " · "
        );

    elements.profileCvUploadedAt
        .textContent =
            formatCvUploadedAt(
                currentUserCv
                    .uploaded_at
            );
}


async function loadUserCv() {
    clearProfileCvMessage();

    elements.profileCvEmpty
        .classList
        .add(
            "hidden"
        );

    elements.profileCvCurrent
        .classList
        .add(
            "hidden"
        );

    elements.profileCvLoading
        .classList
        .remove(
            "hidden"
        );

    try {
        const response =
            await apiFetch(
                "/user-cv"
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
                    "Je basis-CV kon "
                    + "niet worden geladen."
                )
            );
        }

        currentUserCv =
            await response.json();

        renderUserCv();

        syncProfileCvProcessing();

    } catch (error) {
        console.error(
            error
        );

        cancelProfileCvPolling();

        currentUserCv = null;

        elements.profileCvLoading
            .classList
            .add(
                "hidden"
            );

        showProfileCvMessage(
            error.message
            || (
                "Je basis-CV kon "
                + "niet worden geladen."
            )
        );
    }
}


async function uploadUserCv(
    file
) {
    if (!file) {
        return;
    }

    clearProfileCvMessage();

    const filename =
        String(
            file.name || ""
        );

    if (
        !/\.(pdf|docx)$/i
            .test(
                filename
            )
    ) {
        showProfileCvMessage(
            "Alleen PDF- en DOCX-bestanden "
            + "worden ondersteund."
        );

        elements.profileCvInput.value =
            "";

        return;
    }

    if (
        file.size === 0
    ) {
        showProfileCvMessage(
            "Het geselecteerde bestand is leeg."
        );

        elements.profileCvInput.value =
            "";

        return;
    }

    if (
        file.size
        > 10 * 1024 * 1024
    ) {
        showProfileCvMessage(
            "Het CV mag maximaal 10 MB zijn."
        );

        elements.profileCvInput.value =
            "";

        return;
    }

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    setProfileCvBusy(
        true
    );

    showProfileCvMessage(
        "CV wordt geüpload...",
        "success"
    );

    try {
        const response =
            await apiFetch(
                "/user-cv",
                {
                    method: "POST",
                    body: formData,
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
                    "Het CV kon niet "
                    + "worden geüpload."
                )
            );
        }

        currentUserCv =
            await response.json();

        renderUserCv();

        syncProfileCvProcessing(
            {
                afterUpload: true,
            }
        );

    } catch (error) {
        console.error(
            error
        );

        showProfileCvMessage(
            error.message
            || (
                "Het CV kon niet "
                + "worden geüpload."
            )
        );

    } finally {
        elements.profileCvInput
            .value = "";

        setProfileCvBusy(
            false
        );
    }
}


async function downloadUserCv() {
    if (!currentUserCv) {
        return;
    }

    clearProfileCvMessage();

    setProfileCvBusy(
        true
    );

    try {
        const response =
            await apiFetch(
                "/user-cv/download"
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
                    "Het CV kon niet "
                    + "worden gedownload."
                )
            );
        }

        const blob =
            await response.blob();

        const objectUrl =
            URL.createObjectURL(
                blob
            );

        const link =
            document.createElement(
                "a"
            );

        link.href =
            objectUrl;

        link.download =
            currentUserCv
                .original_filename
            || "Civora_CV";

        document.body
            .appendChild(
                link
            );

        link.click();
        link.remove();

        window.setTimeout(
            () => {
                URL.revokeObjectURL(
                    objectUrl
                );
            },
            1000
        );

    } catch (error) {
        console.error(
            error
        );

        showProfileCvMessage(
            error.message
            || (
                "Het CV kon niet "
                + "worden gedownload."
            )
        );

    } finally {
        setProfileCvBusy(
            false
        );
    }
}


async function deleteUserCv() {
    if (!currentUserCv) {
        return;
    }

    const confirmed =
        window.confirm(
            "Weet je zeker dat je dit "
            + "basis-CV wilt verwijderen?"
        );

    if (!confirmed) {
        return;
    }

    clearProfileCvMessage();

    setProfileCvBusy(
        true
    );

    try {
        const response =
            await apiFetch(
                "/user-cv",
                {
                    method: "DELETE",
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
                    "Het CV kon niet "
                    + "worden verwijderd."
                )
            );
        }

        currentUserCv = null;

        renderUserCv();

        showProfileCvMessage(
            "Je basis-CV is verwijderd.",
            "success"
        );

    } catch (error) {
        console.error(
            error
        );

        showProfileCvMessage(
            error.message
            || (
                "Het CV kon niet "
                + "worden verwijderd."
            )
        );

    } finally {
        setProfileCvBusy(
            false
        );
    }
}


async function openProfile() {
    if (!currentUser) {
        return;
    }

    closeDrawer();

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

    clearProfileCvMessage();

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

    await loadUserCv();
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

        state.feed = "for_you";

        updateFeedControls();

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

function formatVakgroep(
    value
) {
    const labels = {
        procesmanagement:
            "Procesmanagement",
        data_ai:
            "Data & AI",
        ict:
            "ICT",
        finance:
            "Finance",
        overige:
            "Overige",
    };

    return (
        labels[value]
        || "Jouw vakgroep"
    );
}

function updateFeedControls() {
    const isForYou =
        state.feed === "for_you";

    elements.feedForYou
        .classList
        .toggle(
            "active",
            isForYou
        );

    elements.feedAll
        .classList
        .toggle(
            "active",
            !isForYou
        );

    elements.feedForYou
        .setAttribute(
            "aria-pressed",
            String(isForYou)
        );

    elements.feedAll
        .setAttribute(
            "aria-pressed",
            String(!isForYou)
        );

    if (isForYou) {
        elements.feedTitle
            .textContent =
                "Voor jou";

        elements.feedDescription
            .textContent =
                "Opdrachten die aansluiten "
                + "op jouw vakgroep, "
                + "gerangschikt op relevantie.";

        return;
    }

    elements.feedTitle
        .textContent =
            "Alle opdrachten";

    elements.feedDescription
        .textContent =
            "Bekijk alle actieve publieke "
            + "inhuuropdrachten in Civora.";
}


async function setFeed(
    feed
) {
    if (
        ![
            "for_you",
            "all",
        ].includes(
            feed
        )
    ) {
        return;
    }

    if (
        state.loading
        || state.feed === feed
    ) {
        return;
    }

    state.feed = feed;
    state.offset = 0;

    updateFeedControls();

    await loadOpportunities();
}

function createCard(item) {
    const article =
        document.createElement(
            "article"
        );

    article.className =
        "opportunity-card";

    article.tabIndex = 0;

    const relevanceScore =
        Number(
            item.relevance_score
        );

    const showMatch =
        state.feed === "for_you"
        && Number.isFinite(
            relevanceScore
        );

    const matchMarkup =
        showMatch
            ? `
                <div class="card-match-row">
                    <span class="match-badge">
                        ${escapeHtml(
                            formatVakgroep(
                                item.matched_vakgroep
                            )
                        )}
                        ·
                        ${Math.round(
                            relevanceScore
                        )}% match
                    </span>
                </div>
            `
            : "";

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

        ${matchMarkup}

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

function renderEmptyState() {
    if (
        state.feed === "for_you"
    ) {
        elements.empty.innerHTML = `
            <div class="empty-icon">
                C
            </div>

            <h3>
                Geen passende opdrachten gevonden
            </h3>

            <p>
                Er zijn momenteel geen opdrachten
                die aansluiten op jouw vakgroep
                en de gekozen filters.
            </p>

            <button
                type="button"
                class="
                    button
                    button-secondary
                    empty-view-all
                "
            >
                Bekijk alle opdrachten
            </button>
        `;

        elements.empty
            .querySelector(
                ".empty-view-all"
            )
            ?.addEventListener(
                "click",
                () => {
                    setFeed(
                        "all"
                    );
                }
            );

        return;
    }

    elements.empty.innerHTML = `
        <div class="empty-icon">
            C
        </div>

        <h3>
            Geen opdrachten gevonden
        </h3>

        <p>
            Pas je filters aan en
            probeer het opnieuw.
        </p>
    `;
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

        elements.loadMoreContainer
            .classList
            .add(
                "hidden"
            );
    }

    const params = getFilters();

    params.set(
        "feed",
        state.feed
    );

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

            renderEmptyState();

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

        if (
            state.feed === "for_you"
        ) {
            elements.resultsMeta
                .textContent =
                    state.offset === 1
                        ? "1 passende opdracht geladen"
                        : `${state.offset} passende opdrachten geladen`;
        } else {
            elements.resultsMeta
                .textContent =
                    state.offset === 1
                        ? "1 opdracht geladen"
                        : `${state.offset} opdrachten geladen`;
        }

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

elements.profileCvUpload
    .addEventListener(
        "click",
        () => {
            elements.profileCvInput
                .click();
        }
    );


elements.profileCvReplace
    .addEventListener(
        "click",
        () => {
            elements.profileCvInput
                .click();
        }
    );


elements.profileCvInput
    .addEventListener(
        "change",
        async () => {
            const file =
                elements.profileCvInput
                    .files?.[0];

            if (!file) {
                return;
            }

            await uploadUserCv(
                file
            );
        }
    );


elements.profileCvDownload
    .addEventListener(
        "click",
        downloadUserCv
    );


elements.profileCvDelete
    .addEventListener(
        "click",
        deleteUserCv
    );

elements.feedForYou
    .addEventListener(
        "click",
        () => {
            setFeed(
                "for_you"
            );
        }
    );


elements.feedAll
    .addEventListener(
        "click",
        () => {
            setFeed(
                "all"
            );
        }
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
                currentUserCv = null;

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