"""Validatie en Storage-functies voor gebruikers-CV's."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import unicodedata
from zipfile import (
    BadZipFile,
    ZipFile,
)

from backend.app.database.client import (
    get_supabase_client,
)


USER_CV_BUCKET = "user-cvs"

MAX_CV_SIZE_BYTES = (
    10 * 1024 * 1024
)

PDF_MIME_TYPE = (
    "application/pdf"
)

DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


class CvValidationError(
    ValueError
):
    """Basisfout voor een ongeldig CV."""


class CvFileTooLargeError(
    CvValidationError
):
    """CV overschrijdt maximale bestandsgrootte."""


class UnsupportedCvFileError(
    CvValidationError
):
    """Niet-ondersteund CV-bestandstype."""


class InvalidCvFileError(
    CvValidationError
):
    """Bestandsinhoud komt niet overeen met het type."""


@dataclass(
    frozen=True,
    slots=True,
)
class ValidatedCvFile:
    """Gevalideerde metadata van een CV."""

    original_filename: str
    extension: str
    mime_type: str
    file_size_bytes: int
    sha256: str


def sanitize_filename(
    filename: str | None,
) -> str:
    """Normaliseer een client-bestandsnaam voor weergave."""

    if not filename:
        raise CvValidationError(
            "Bestandsnaam ontbreekt."
        )

    normalized = (
        unicodedata.normalize(
            "NFKC",
            filename,
        )
    )

    basename = Path(
        normalized
    ).name

    basename = "".join(
        character
        for character in basename
        if character.isprintable()
    ).strip()

    if not basename:
        raise CvValidationError(
            "Bestandsnaam is ongeldig."
        )

    return basename[:255]


def _validate_pdf(
    content: bytes,
) -> None:
    """Controleer de PDF-signatuur."""

    if (
        b"%PDF-"
        not in content[:1024]
    ):
        raise InvalidCvFileError(
            "Het bestand is geen geldige PDF."
        )


def _validate_docx(
    content: bytes,
) -> None:
    """Controleer minimale DOCX ZIP-structuur."""

    try:
        with ZipFile(
            BytesIO(content)
        ) as archive:
            names = set(
                archive.namelist()
            )

    except BadZipFile as exc:
        raise InvalidCvFileError(
            "Het bestand is geen geldige DOCX."
        ) from exc

    required_entries = {
        "[Content_Types].xml",
        "word/document.xml",
    }

    if not required_entries.issubset(
        names
    ):
        raise InvalidCvFileError(
            "Het bestand bevat geen geldige "
            "DOCX-documentstructuur."
        )


def validate_cv_file(
    *,
    filename: str | None,
    content: bytes,
) -> ValidatedCvFile:
    """Valideer bestandsgrootte, extensie en inhoud."""

    clean_filename = (
        sanitize_filename(
            filename
        )
    )

    file_size = len(
        content
    )

    if file_size == 0:
        raise CvValidationError(
            "Het CV-bestand is leeg."
        )

    if (
        file_size
        > MAX_CV_SIZE_BYTES
    ):
        raise CvFileTooLargeError(
            "Het CV mag maximaal 10 MB zijn."
        )

    extension = (
        Path(
            clean_filename
        )
        .suffix
        .casefold()
    )

    if extension == ".pdf":
        mime_type = (
            PDF_MIME_TYPE
        )

        _validate_pdf(
            content
        )

    elif extension == ".docx":
        mime_type = (
            DOCX_MIME_TYPE
        )

        _validate_docx(
            content
        )

    else:
        raise UnsupportedCvFileError(
            "Alleen PDF- en DOCX-bestanden "
            "worden ondersteund."
        )

    return ValidatedCvFile(
        original_filename=(
            clean_filename
        ),
        extension=extension,
        mime_type=mime_type,
        file_size_bytes=file_size,
        sha256=(
            sha256(
                content
            ).hexdigest()
        ),
    )


def build_cv_storage_path(
    *,
    user_id: str,
    cv_id: str,
    extension: str,
) -> str:
    """Maak een server-side Storage-pad."""

    safe_extension = (
        extension.casefold()
    )

    if safe_extension not in {
        ".pdf",
        ".docx",
    }:
        raise ValueError(
            "Ongeldige CV-extensie."
        )

    return (
        f"{user_id}/"
        f"{cv_id}/"
        f"source{safe_extension}"
    )


def upload_user_cv_file(
    *,
    storage_path: str,
    content: bytes,
    mime_type: str,
) -> None:
    """Upload een CV naar de private bucket."""

    client = (
        get_supabase_client()
    )

    (
        client.storage
        .from_(
            USER_CV_BUCKET
        )
        .upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": (
                    mime_type
                ),
                "upsert": "false",
            },
        )
    )


def remove_user_cv_file(
    *,
    storage_path: str,
) -> None:
    """Verwijder één CV-object uit Storage."""

    client = (
        get_supabase_client()
    )

    (
        client.storage
        .from_(
            USER_CV_BUCKET
        )
        .remove(
            [
                storage_path
            ]
        )
    )