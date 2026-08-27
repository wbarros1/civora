"""Deterministische validatie van geëxtraheerde kandidaatprofielen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.schemas.candidate_profile import (
    CandidateProfile,
    EvidenceBackedText,
    EvidenceSnippet,
)
from backend.app.services.candidate_profile_extractor import (
    CandidateProfileExtractionResult,
)
from backend.app.services.candidate_profile_input import (
    PreparedCandidateProfileInput,
    normalize_evidence_comparison,
    verify_candidate_profile_evidence,
)


ValidationSeverity = Literal[
    "error",
    "review",
]


@dataclass(
    frozen=True,
    slots=True,
)
class CandidateProfileValidationIssue:
    """Eén deterministische validatiebevinding."""

    code: str
    severity: ValidationSeverity
    path: str
    message: str


@dataclass(
    frozen=True,
    slots=True,
)
class CandidateProfileValidationResult:
    """Volledige validatie-uitkomst."""

    issues: tuple[
        CandidateProfileValidationIssue,
        ...
    ]

    total_evidence_snippets: int
    verified_evidence_snippets: int

    atomic_claims_checked: int
    atomic_claims_verified: int

    @property
    def errors(
        self,
    ) -> tuple[
        CandidateProfileValidationIssue,
        ...
    ]:
        """Geef uitsluitend blokkerende fouten terug."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == "error"
        )

    @property
    def review_issues(
        self,
    ) -> tuple[
        CandidateProfileValidationIssue,
        ...
    ]:
        """Geef reviewbevindingen terug."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == "review"
        )

    @property
    def is_valid(
        self,
    ) -> bool:
        """Een profiel is geldig zonder blocking errors."""

        return not self.errors

    @property
    def requires_review(
        self,
    ) -> bool:
        """Review is nodig bij een niet-blokkerende onzekerheid."""

        return bool(
            self.review_issues
        )


def _value_exists_in_source(
    *,
    value: str,
    source_text: str,
) -> bool:
    """Controleer een korte atomaire waarde tegen de bron."""

    normalized_value = (
        normalize_evidence_comparison(
            value
        )
    )

    normalized_source = (
        normalize_evidence_comparison(
            source_text
        )
    )

    if not normalized_value:
        return False

    return (
        normalized_value
        in normalized_source
    )


def _value_exists_in_evidence(
    *,
    value: str,
    evidence: list[
        EvidenceSnippet
    ],
) -> bool:
    """
    Controleer of een atomaire claim door
    minimaal één evidencefragment wordt gedragen.
    """

    normalized_value = (
        normalize_evidence_comparison(
            value
        )
    )

    if not normalized_value:
        return False

    for snippet in evidence:
        normalized_evidence = (
            normalize_evidence_comparison(
                snippet.text
            )
        )

        if (
            normalized_value
            in normalized_evidence
        ):
            return True

    return False


def _validate_atomic_value(
    *,
    path: str,
    value: str | None,
    evidence: list[
        EvidenceSnippet
    ],
    source_text: str,
    issues: list[
        CandidateProfileValidationIssue
    ],
) -> tuple[
    int,
    int,
]:
    """
    Valideer één korte feitelijke claim.

    Returns:
        (aantal gecontroleerd, aantal geverifieerd)
    """

    if value is None:
        return (
            0,
            0,
        )

    cleaned_value = (
        " ".join(
            value.split()
        ).strip()
    )

    if not cleaned_value:
        return (
            0,
            0,
        )

    checked = 1

    source_valid = (
        _value_exists_in_source(
            value=cleaned_value,
            source_text=source_text,
        )
    )

    evidence_valid = (
        _value_exists_in_evidence(
            value=cleaned_value,
            evidence=evidence,
        )
    )

    if not source_valid:
        issues.append(
            CandidateProfileValidationIssue(
                code=(
                    "atomic_value_not_in_source"
                ),
                severity="error",
                path=path,
                message=(
                    "Een feitelijke profielwaarde "
                    "komt niet letterlijk voor in "
                    "de CV-bron."
                ),
            )
        )

    if not evidence_valid:
        issues.append(
            CandidateProfileValidationIssue(
                code=(
                    "atomic_value_not_supported_by_evidence"
                ),
                severity="error",
                path=path,
                message=(
                    "Een feitelijke profielwaarde "
                    "wordt niet gedragen door het "
                    "gekoppelde bronbewijs."
                ),
            )
        )

    if (
        source_valid
        and evidence_valid
    ):
        return (
            checked,
            1,
        )

    return (
        checked,
        0,
    )


def _validate_evidence_backed_text(
    *,
    path: str,
    value: (
        EvidenceBackedText
        | None
    ),
    source_text: str,
    issues: list[
        CandidateProfileValidationIssue
    ],
) -> tuple[
    int,
    int,
]:
    """Valideer een EvidenceBackedText-claim."""

    if value is None:
        return (
            0,
            0,
        )

    return _validate_atomic_value(
        path=path,
        value=value.value,
        evidence=value.evidence,
        source_text=source_text,
        issues=issues,
    )


def _profile_has_meaningful_content(
    profile: CandidateProfile,
) -> bool:
    """Controleer of de extractie feitelijke inhoud bevat."""

    contact = (
        profile.contact_information
    )

    has_contact = any(
        [
            contact.email,
            contact.phone,
            contact.location,
            contact.linkedin_url,
            contact.website_url,
        ]
    )

    return any(
        [
            profile.full_name,
            profile.headline,
            has_contact,
            profile.work_experience,
            profile.education,
            profile.certifications,
            profile.skills,
            profile.competencies,
            profile.tools_and_technologies,
            profile.languages,
        ]
    )


def validate_candidate_profile_extraction(
    *,
    extraction_result: (
        CandidateProfileExtractionResult
    ),
    prepared_input: (
        PreparedCandidateProfileInput
    ),
) -> CandidateProfileValidationResult:
    """
    Valideer LLM-output deterministisch
    tegen exact dezelfde CV-input.
    """

    issues: list[
        CandidateProfileValidationIssue
    ] = []

    extraction = (
        extraction_result.extraction
    )

    profile = extraction.profile

    source_text = (
        prepared_input.text
    )

    if (
        extraction_result.input_sha256
        != prepared_input.input_sha256
    ):
        issues.append(
            CandidateProfileValidationIssue(
                code="input_hash_mismatch",
                severity="error",
                path="input_sha256",
                message=(
                    "Het kandidaatprofiel hoort "
                    "niet bij dezelfde CV-input."
                ),
            )
        )

    if not _profile_has_meaningful_content(
        profile
    ):
        issues.append(
            CandidateProfileValidationIssue(
                code="empty_candidate_profile",
                severity="error",
                path="profile",
                message=(
                    "De extractie bevat geen "
                    "bruikbare feitelijke "
                    "kandidaatinformatie."
                ),
            )
        )

    evidence_result = (
        verify_candidate_profile_evidence(
            profile=profile,
            source_text=source_text,
        )
    )

    if not evidence_result.is_valid:
        issues.append(
            CandidateProfileValidationIssue(
                code="unverified_evidence",
                severity="error",
                path="profile",
                message=(
                    "Een of meer evidencefragmenten "
                    "komen niet letterlijk voor "
                    "in de CV-bron."
                ),
            )
        )

    atomic_claims_checked = 0
    atomic_claims_verified = 0

    def validate_atomic(
        *,
        path: str,
        value: str | None,
        evidence: list[
            EvidenceSnippet
        ],
    ) -> None:
        nonlocal atomic_claims_checked, atomic_claims_verified

        (
            checked,
            verified,
        ) = _validate_atomic_value(
            path=path,
            value=value,
            evidence=evidence,
            source_text=source_text,
            issues=issues,
        )

        atomic_claims_checked += (
            checked
        )

        atomic_claims_verified += (
            verified
        )

    def validate_backed(
        *,
        path: str,
        value: (
            EvidenceBackedText
            | None
        ),
    ) -> None:
        nonlocal atomic_claims_checked, atomic_claims_verified

        (
            checked,
            verified,
        ) = (
            _validate_evidence_backed_text(
                path=path,
                value=value,
                source_text=source_text,
                issues=issues,
            )
        )

        atomic_claims_checked += (
            checked
        )

        atomic_claims_verified += (
            verified
        )

    validate_backed(
        path="profile.full_name",
        value=profile.full_name,
    )

    validate_backed(
        path="profile.headline",
        value=profile.headline,
    )

    contact = (
        profile.contact_information
    )

    validate_backed(
        path=(
            "profile.contact_information.email"
        ),
        value=contact.email,
    )

    validate_backed(
        path=(
            "profile.contact_information.phone"
        ),
        value=contact.phone,
    )

    validate_backed(
        path=(
            "profile.contact_information.location"
        ),
        value=contact.location,
    )

    validate_backed(
        path=(
            "profile.contact_information.linkedin_url"
        ),
        value=contact.linkedin_url,
    )

    validate_backed(
        path=(
            "profile.contact_information.website_url"
        ),
        value=contact.website_url,
    )

    for index, item in enumerate(
        profile.work_experience
    ):
        prefix = (
            "profile.work_experience"
            f"[{index}]"
        )

        validate_atomic(
            path=f"{prefix}.job_title",
            value=item.job_title,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.organization",
            value=item.organization,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.client_name",
            value=item.client_name,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.location",
            value=item.location,
            evidence=item.evidence,
        )

        for technology_index, technology in enumerate(
            item.technologies
        ):
            validate_atomic(
                path=(
                    f"{prefix}.technologies"
                    f"[{technology_index}]"
                ),
                value=technology,
                evidence=item.evidence,
            )

    for index, item in enumerate(
        profile.education
    ):
        prefix = (
            "profile.education"
            f"[{index}]"
        )

        validate_atomic(
            path=f"{prefix}.program_name",
            value=item.program_name,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.institution",
            value=item.institution,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.level",
            value=item.level,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.location",
            value=item.location,
            evidence=item.evidence,
        )

    for index, item in enumerate(
        profile.certifications
    ):
        prefix = (
            "profile.certifications"
            f"[{index}]"
        )

        validate_atomic(
            path=f"{prefix}.name",
            value=item.name,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.issuer",
            value=item.issuer,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.credential_id",
            value=item.credential_id,
            evidence=item.evidence,
        )

    for index, item in enumerate(
        profile.skills
    ):
        validate_backed(
            path=(
                "profile.skills"
                f"[{index}]"
            ),
            value=item,
        )

    for index, item in enumerate(
        profile.competencies
    ):
        validate_backed(
            path=(
                "profile.competencies"
                f"[{index}]"
            ),
            value=item,
        )

    for index, item in enumerate(
        profile.tools_and_technologies
    ):
        validate_backed(
            path=(
                "profile.tools_and_technologies"
                f"[{index}]"
            ),
            value=item,
        )

    for index, item in enumerate(
        profile.languages
    ):
        prefix = (
            "profile.languages"
            f"[{index}]"
        )

        validate_atomic(
            path=f"{prefix}.language",
            value=item.language,
            evidence=item.evidence,
        )

        validate_atomic(
            path=f"{prefix}.level",
            value=item.level,
            evidence=item.evidence,
        )

    if (
        extraction.overall_confidence
        < 0.60
    ):
        issues.append(
            CandidateProfileValidationIssue(
                code="low_confidence",
                severity="review",
                path="overall_confidence",
                message=(
                    "De LLM-confidence is lager "
                    "dan de reviewdrempel van 0,60."
                ),
            )
        )

    for index, reason in enumerate(
        extraction.review_reasons
    ):
        issues.append(
            CandidateProfileValidationIssue(
                code="llm_review_reason",
                severity="review",
                path=(
                    "review_reasons"
                    f"[{index}]"
                ),
                message=reason,
            )
        )

    return CandidateProfileValidationResult(
        issues=tuple(
            issues
        ),
        total_evidence_snippets=(
            evidence_result.total_snippets
        ),
        verified_evidence_snippets=(
            evidence_result.verified_snippets
        ),
        atomic_claims_checked=(
            atomic_claims_checked
        ),
        atomic_claims_verified=(
            atomic_claims_verified
        ),
    )