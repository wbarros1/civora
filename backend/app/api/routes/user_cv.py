"""API-routes voor het basis-CV van een gebruiker."""

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from backend.app.dependencies.auth import (
    get_current_identity,
)
from backend.app.repositories.user_cvs import (
    activate_user_cv,
    create_user_cv,
    delete_user_cv_record,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)
from backend.app.schemas.user_cv import (
    UserCvResponse,
)
from backend.app.services.user_cv_files import (
    CvFileTooLargeError,
    CvValidationError,
    MAX_CV_SIZE_BYTES,
    UnsupportedCvFileError,
    build_cv_storage_path,
    remove_user_cv_file,
    upload_user_cv_file,
    validate_cv_file,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()


@router.post(
    "",
    response_model=UserCvResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
    summary="Upload of vervang het basis-CV",
)
async def upload_user_cv(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Basis-CV als PDF of DOCX, "
                "maximaal 10 MB."
            )
        ),
    ],
) -> UserCvResponse:
    """Upload een nieuwe actieve versie van het basis-CV."""

    try:
        content = await file.read(
            MAX_CV_SIZE_BYTES
            + 1
        )

    finally:
        await file.close()

    try:
        validated = (
            validate_cv_file(
                filename=file.filename,
                content=content,
            )
        )

    except CvFileTooLargeError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=str(
                exc
            ),
        ) from exc

    except UnsupportedCvFileError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=str(
                exc
            ),
        ) from exc

    except CvValidationError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(
                exc
            ),
        ) from exc


    cv_id = str(
        uuid4()
    )

    storage_path = (
        build_cv_storage_path(
            user_id=identity.id,
            cv_id=cv_id,
            extension=(
                validated.extension
            ),
        )
    )


    storage_uploaded = False
    database_record_created = False

    try:
        upload_user_cv_file(
            storage_path=storage_path,
            content=content,
            mime_type=(
                validated.mime_type
            ),
        )

        storage_uploaded = True

        create_user_cv(
            cv_id=cv_id,
            user_id=identity.id,
            original_filename=(
                validated
                .original_filename
            ),
            storage_path=(
                storage_path
            ),
            mime_type=(
                validated.mime_type
            ),
            file_size_bytes=(
                validated
                .file_size_bytes
            ),
            sha256_hash=(
                validated.sha256
            ),
        )

        database_record_created = True

        active_cv = (
            activate_user_cv(
                user_id=identity.id,
                cv_id=cv_id,
            )
        )

    except Exception as exc:
        logger.exception(
            "Upload van basis-CV is mislukt."
        )

        if database_record_created:
            try:
                delete_user_cv_record(
                    user_id=identity.id,
                    cv_id=cv_id,
                )

            except Exception:
                logger.exception(
                    "Rollback van CV-record "
                    "is mislukt."
                )

        if storage_uploaded:
            try:
                remove_user_cv_file(
                    storage_path=(
                        storage_path
                    ),
                )

            except Exception:
                logger.exception(
                    "Rollback van CV-bestand "
                    "in Storage is mislukt."
                )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet worden opgeslagen."
            ),
        ) from exc


    return UserCvResponse(
        **active_cv
    )