"""Tests voor CV-bestandsvalidatie."""

from io import BytesIO
from zipfile import ZipFile

import pytest

from backend.app.services.user_cv_files import (
    CvFileTooLargeError,
    InvalidCvFileError,
    MAX_CV_SIZE_BYTES,
    UnsupportedCvFileError,
    build_cv_storage_path,
    validate_cv_file,
)


def make_minimal_docx() -> bytes:
    """Maak minimale DOCX-structuur voor validatietests."""

    buffer = BytesIO()

    with ZipFile(
        buffer,
        "w",
    ) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types></Types>",
        )

        archive.writestr(
            "word/document.xml",
            "<document></document>",
        )

    return buffer.getvalue()


def test_valid_pdf() -> None:
    result = validate_cv_file(
        filename="CV Test.pdf",
        content=(
            b"%PDF-1.7\n"
            b"test"
        ),
    )

    assert (
        result.extension
        == ".pdf"
    )

    assert (
        result.mime_type
        == "application/pdf"
    )

    assert (
        len(result.sha256)
        == 64
    )


def test_fake_pdf_is_rejected() -> None:
    with pytest.raises(
        InvalidCvFileError
    ):
        validate_cv_file(
            filename="cv.pdf",
            content=b"geen pdf",
        )


def test_valid_docx() -> None:
    result = validate_cv_file(
        filename="CV Test.docx",
        content=make_minimal_docx(),
    )

    assert (
        result.extension
        == ".docx"
    )


def test_fake_docx_is_rejected() -> None:
    with pytest.raises(
        InvalidCvFileError
    ):
        validate_cv_file(
            filename="cv.docx",
            content=b"geen docx",
        )


def test_unsupported_extension_is_rejected() -> None:
    with pytest.raises(
        UnsupportedCvFileError
    ):
        validate_cv_file(
            filename="cv.txt",
            content=b"test",
        )


def test_file_above_limit_is_rejected() -> None:
    with pytest.raises(
        CvFileTooLargeError
    ):
        validate_cv_file(
            filename="cv.pdf",
            content=(
                b"%PDF-"
                + (
                    b"x"
                    * MAX_CV_SIZE_BYTES
                )
            ),
        )


def test_storage_path_is_server_generated() -> None:
    result = build_cv_storage_path(
        user_id="user-1",
        cv_id="cv-1",
        extension=".pdf",
    )

    assert result == (
        "user-1/"
        "cv-1/"
        "source.pdf"
    )