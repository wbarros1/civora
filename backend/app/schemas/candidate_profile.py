"""Pydantic-schema's voor gestructureerde kandidaatprofielen."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def normalize_text_list(
    values: list[str],
) -> list[str]:
    """Normaliseer en dedupliceer tekstwaarden."""

    normalized_values: list[str] = []
    seen_values: set[str] = set()

    for value in values:
        cleaned_value = " ".join(
            value.split()
        ).strip()

        if not cleaned_value:
            continue

        comparison_value = (
            cleaned_value.casefold()
        )

        if comparison_value in seen_values:
            continue

        seen_values.add(
            comparison_value
        )

        normalized_values.append(
            cleaned_value
        )

    return normalized_values


class CandidateDate(BaseModel):
    """
    Datum uit een CV.

    De maand blijft leeg wanneer alleen
    een jaartal expliciet in het CV staat.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    year: int = Field(
        ge=1900,
        le=2100,
    )

    month: int | None = Field(
        default=None,
        ge=1,
        le=12,
    )


class EvidenceSnippet(BaseModel):
    """Letterlijk bewijs uit de uitgelezen CV-tekst."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(
        min_length=1,
        max_length=600,
    )

    @field_validator(
        "text"
    )
    @classmethod
    def normalize_evidence_text(
        cls,
        value: str,
    ) -> str:
        """Normaliseer witruimte zonder inhoud te wijzigen."""

        return " ".join(
            value.split()
        ).strip()


class EvidenceBackedText(BaseModel):
    """Korte CV-waarde met minimaal één bewijsfragment."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    value: str = Field(
        min_length=1,
        max_length=500,
    )

    evidence: list[
        EvidenceSnippet
    ] = Field(
        min_length=1,
        max_length=5,
    )

    @field_validator(
        "value"
    )
    @classmethod
    def normalize_value(
        cls,
        value: str,
    ) -> str:
        """Normaliseer witruimte."""

        return " ".join(
            value.split()
        ).strip()

    @field_validator(
        "evidence"
    )
    @classmethod
    def deduplicate_evidence(
        cls,
        values: list[
            EvidenceSnippet
        ],
    ) -> list[
        EvidenceSnippet
    ]:
        """Verwijder dubbele bewijsfragmenten."""

        normalized_values: list[
            EvidenceSnippet
        ] = []

        seen_values: set[str] = set()

        for value in values:
            comparison_value = (
                value.text.casefold()
            )

            if (
                comparison_value
                in seen_values
            ):
                continue

            seen_values.add(
                comparison_value
            )

            normalized_values.append(
                value
            )

        return normalized_values


class EvidenceBackedNarrative(BaseModel):
    """Langere CV-tekst met bronbewijs."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    value: str = Field(
        min_length=1,
        max_length=3000,
    )

    evidence: list[
        EvidenceSnippet
    ] = Field(
        min_length=1,
        max_length=10,
    )

    @field_validator(
        "value"
    )
    @classmethod
    def normalize_value(
        cls,
        value: str,
    ) -> str:
        """Normaliseer witruimte."""

        return " ".join(
            value.split()
        ).strip()

    @field_validator(
        "evidence"
    )
    @classmethod
    def deduplicate_evidence(
        cls,
        values: list[
            EvidenceSnippet
        ],
    ) -> list[
        EvidenceSnippet
    ]:
        """Verwijder dubbele bewijsfragmenten."""

        normalized_values: list[
            EvidenceSnippet
        ] = []

        seen_values: set[str] = set()

        for value in values:
            comparison_value = (
                value.text.casefold()
            )

            if (
                comparison_value
                in seen_values
            ):
                continue

            seen_values.add(
                comparison_value
            )

            normalized_values.append(
                value
            )

        return normalized_values


class CandidateContactInformation(
    BaseModel
):
    """Contactinformatie die expliciet in het CV staat."""

    model_config = ConfigDict(
        extra="forbid",
    )

    email: (
        EvidenceBackedText
        | None
    ) = None

    phone: (
        EvidenceBackedText
        | None
    ) = None

    location: (
        EvidenceBackedText
        | None
    ) = None

    linkedin_url: (
        EvidenceBackedText
        | None
    ) = None

    website_url: (
        EvidenceBackedText
        | None
    ) = None


def validate_date_range(
    *,
    start_date: (
        CandidateDate
        | None
    ),
    end_date: (
        CandidateDate
        | None
    ),
) -> None:
    """
    Controleer alleen ranges die voldoende
    expliciete datumprecisie bevatten.
    """

    if (
        start_date is None
        or end_date is None
    ):
        return

    if (
        end_date.year
        < start_date.year
    ):
        raise ValueError(
            "end_date mag niet vóór "
            "start_date liggen."
        )

    if (
        end_date.year
        == start_date.year
        and start_date.month
        is not None
        and end_date.month
        is not None
        and end_date.month
        < start_date.month
    ):
        raise ValueError(
            "end_date mag niet vóór "
            "start_date liggen."
        )


class WorkExperience(BaseModel):
    """Eén aantoonbare werkervaring uit het CV."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    job_title: str | None = Field(
        default=None,
        max_length=500,
    )

    organization: str | None = Field(
        default=None,
        max_length=500,
    )

    client_name: str | None = Field(
        default=None,
        max_length=500,
    )

    location: str | None = Field(
        default=None,
        max_length=500,
    )

    start_date: (
        CandidateDate
        | None
    ) = None

    end_date: (
        CandidateDate
        | None
    ) = None

    is_current: bool | None = None

    description: str | None = Field(
        default=None,
        max_length=3000,
    )

    activities: list[str] = Field(
        default_factory=list,
        max_length=25,
    )

    technologies: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    evidence: list[
        EvidenceSnippet
    ] = Field(
        min_length=1,
        max_length=10,
    )

    @field_validator(
        "activities",
        "technologies",
    )
    @classmethod
    def normalize_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        """Normaliseer activiteiten en technologieën."""

        return normalize_text_list(
            values
        )

    @model_validator(
        mode="after"
    )
    def validate_experience(
        self,
    ) -> "WorkExperience":
        """Controleer inhoud en datums."""

        has_content = any(
            [
                self.job_title,
                self.organization,
                self.client_name,
                self.description,
                self.activities,
                self.technologies,
            ]
        )

        if not has_content:
            raise ValueError(
                "Werkervaring moet minimaal "
                "één inhoudelijk veld bevatten."
            )

        if (
            self.is_current is True
            and self.end_date
            is not None
        ):
            raise ValueError(
                "Een huidige functie mag "
                "geen end_date hebben."
            )

        validate_date_range(
            start_date=(
                self.start_date
            ),
            end_date=(
                self.end_date
            ),
        )

        return self


class EducationEntry(BaseModel):
    """Eén opleiding uit het CV."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    program_name: str | None = Field(
        default=None,
        max_length=500,
    )

    institution: str | None = Field(
        default=None,
        max_length=500,
    )

    level: str | None = Field(
        default=None,
        max_length=300,
    )

    location: str | None = Field(
        default=None,
        max_length=500,
    )

    start_date: (
        CandidateDate
        | None
    ) = None

    end_date: (
        CandidateDate
        | None
    ) = None

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    evidence: list[
        EvidenceSnippet
    ] = Field(
        min_length=1,
        max_length=8,
    )

    @model_validator(
        mode="after"
    )
    def validate_education(
        self,
    ) -> "EducationEntry":
        """Controleer opleiding en datums."""

        if not any(
            [
                self.program_name,
                self.institution,
                self.level,
                self.description,
            ]
        ):
            raise ValueError(
                "Opleiding moet minimaal "
                "één inhoudelijk veld bevatten."
            )

        validate_date_range(
            start_date=(
                self.start_date
            ),
            end_date=(
                self.end_date
            ),
        )

        return self


class CertificationEntry(BaseModel):
    """Certificering die aantoonbaar in het CV staat."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=500,
    )

    issuer: str | None = Field(
        default=None,
        max_length=500,
    )

    date: (
        CandidateDate
        | None
    ) = None

    credential_id: str | None = Field(
        default=None,
        max_length=500,
    )

    evidence: list[
        EvidenceSnippet
    ] = Field(
        min_length=1,
        max_length=5,
    )


class LanguageEntry(BaseModel):
    """Taalvaardigheid die expliciet in het CV staat."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    language: str = Field(
        min_length=1,
        max_length=200,
    )

    level: str | None = Field(
        default=None,
        max_length=200,
    )

    evidence: list[
        EvidenceSnippet
    ] = Field(
        min_length=1,
        max_length=5,
    )


class CandidateProfile(BaseModel):
    """
    Feitelijk kandidaatprofiel.

    Afgeleide ervaringsjaren horen bewust
    niet in dit schema.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    full_name: (
        EvidenceBackedText
        | None
    ) = None

    headline: (
        EvidenceBackedText
        | None
    ) = None

    profile_summary: (
        EvidenceBackedNarrative
        | None
    ) = None

    contact_information: (
        CandidateContactInformation
    ) = Field(
        default_factory=(
            CandidateContactInformation
        )
    )

    work_experience: list[
        WorkExperience
    ] = Field(
        default_factory=list,
        max_length=50,
    )

    education: list[
        EducationEntry
    ] = Field(
        default_factory=list,
        max_length=30,
    )

    certifications: list[
        CertificationEntry
    ] = Field(
        default_factory=list,
        max_length=30,
    )

    skills: list[
        EvidenceBackedText
    ] = Field(
        default_factory=list,
        max_length=60,
    )

    competencies: list[
        EvidenceBackedText
    ] = Field(
        default_factory=list,
        max_length=40,
    )

    tools_and_technologies: list[
        EvidenceBackedText
    ] = Field(
        default_factory=list,
        max_length=60,
    )

    languages: list[
        LanguageEntry
    ] = Field(
        default_factory=list,
        max_length=20,
    )

    @field_validator(
        "skills",
        "competencies",
        "tools_and_technologies",
    )
    @classmethod
    def deduplicate_evidence_backed_terms(
        cls,
        values: list[
            EvidenceBackedText
        ],
    ) -> list[
        EvidenceBackedText
    ]:
        """Dedupliceer termen op hun inhoudelijke waarde."""

        normalized_values: list[
            EvidenceBackedText
        ] = []

        seen_values: set[str] = set()

        for value in values:
            comparison_value = (
                value.value.casefold()
            )

            if (
                comparison_value
                in seen_values
            ):
                continue

            seen_values.add(
                comparison_value
            )

            normalized_values.append(
                value
            )

        return normalized_values


class CandidateProfileExtractionEnvelope(
    BaseModel
):
    """Volledige gevalideerde output van CV-extractie."""

    model_config = ConfigDict(
        extra="forbid",
    )

    profile: CandidateProfile

    overall_confidence: float = Field(
        ge=0,
        le=1,
    )

    review_reasons: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    @field_validator(
        "review_reasons"
    )
    @classmethod
    def normalize_review_reasons(
        cls,
        values: list[str],
    ) -> list[str]:
        """Normaliseer en dedupliceer reviewredenen."""

        return normalize_text_list(
            values
        )