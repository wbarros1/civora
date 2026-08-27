"""API-routes voor het basis-CV van een gebruiker."""

import logging
from typing import Annotated
from urllib.parse import quote
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
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
    get_active_user_cv,
    is_user_cv_in_use,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)
from backend.app.schemas.user_cv import (
    UserCvResponse,
)

from backend.app.services.candidate_profile_processing import (
    process_user_cv_candidate_profile,
)
from backend.app.services.user_cv_files import (
    CvFileTooLargeError,
    CvValidationError,
    MAX_CV_SIZE_BYTES,
    UnsupportedCvFileError,
    build_cv_storage_path,
    download_user_cv_file,
    remove_user_cv_file,
    upload_user_cv_file,
    validate_cv_file,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()

def process_user_cv_in_background(
    *,
    user_id: str,
    cv_id: str,
) -> None:
    """
    Verwerk een geüpload CV buiten de upload-response.

    Een fout in kandidaatprofielverwerking mag de
    reeds geslaagde CV-upload nooit terugdraaien.
    """

    try:
        process_user_cv_candidate_profile(
            user_id=user_id,
            cv_id=cv_id,
        )

    except Exception as exc:
        # Log bewust alleen het fouttype.
        # CV-inhoud, LLM-output en exception-message
        # worden hier niet gelogd.
        logger.error(
            "Automatische verwerking van "
            "basis-CV is mislukt. "
            "Fouttype=%s",
            type(
                exc
            ).__name__,
        )


@router.get(
    "",
    response_model=(
        UserCvResponse | None
    ),
    summary="Haal het actieve basis-CV op",
)
async def get_current_user_cv(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> UserCvResponse | None:
    """Geef metadata van het actieve basis-CV terug."""

    try:
        active_cv = (
            get_active_user_cv(
                identity.id
            )
        )

    except Exception as exc:
        logger.exception(
            "Basis-CV kon niet "
            "worden opgehaald."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet worden opgehaald."
            ),
        ) from exc

    if active_cv is None:
        return None

    return UserCvResponse(
        **active_cv
    )


@router.get(
    "/download",
    summary="Download het actieve basis-CV",
)
async def download_current_user_cv(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> Response:
    """Download het eigen actieve CV via de backend."""

    try:
        active_cv = (
            get_active_user_cv(
                identity.id
            )
        )

    except Exception as exc:
        logger.exception(
            "CV-metadata kon niet "
            "worden opgehaald."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet worden opgehaald."
            ),
        ) from exc

    if active_cv is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Er is geen actief "
                "basis-CV."
            ),
        )

    storage_path = (
        active_cv.get(
            "storage_path"
        )
    )

    if not isinstance(
        storage_path,
        str,
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Het CV heeft geen "
                "geldig opslagpad."
            ),
        )

    try:
        content = (
            download_user_cv_file(
                storage_path=(
                    storage_path
                )
            )
        )

    except Exception as exc:
        logger.exception(
            "CV kon niet uit private "
            "Storage worden gedownload."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet worden gedownload."
            ),
        ) from exc

    original_filename = str(
        active_cv.get(
            "original_filename"
        )
        or "Civora_CV"
    )

    encoded_filename = quote(
        original_filename,
        safe="",
    )

    mime_type = str(
        active_cv.get(
            "mime_type"
        )
        or "application/octet-stream"
    )

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": (
                "attachment; "
                "filename*=UTF-8''"
                f"{encoded_filename}"
            ),
            "Cache-Control": (
                "private, no-store"
            ),
        },
    )


@router.post(
    "",
    response_model=UserCvResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
    summary="Upload of vervang het basis-CV",
)
async def upload_user_cv(
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        process_user_cv_in_background,
        user_id=identity.id,
        cv_id=cv_id,
    )

    return UserCvResponse(
        **active_cv
    )


@router.delete(
    "",
    status_code=(
        status.HTTP_204_NO_CONTENT
    ),
    summary="Verwijder het actieve basis-CV",
)
async def delete_current_user_cv(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> Response:
    """
    Verwijder het actieve basis-CV.

    Een CV dat al onderdeel is van een
    generation run wordt niet verwijderd.
    """

    try:
        active_cv = (
            get_active_user_cv(
                identity.id
            )
        )

    except Exception as exc:
        logger.exception(
            "CV-metadata kon niet "
            "worden opgehaald."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet worden verwijderd."
            ),
        ) from exc

    if active_cv is None:
        return Response(
            status_code=(
                status.HTTP_204_NO_CONTENT
            )
        )

    cv_id = str(
        active_cv["id"]
    )

    try:
        in_use = (
            is_user_cv_in_use(
                user_id=identity.id,
                cv_id=cv_id,
            )
        )

    except Exception as exc:
        logger.exception(
            "Gebruik van CV kon "
            "niet worden gecontroleerd."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet worden verwijderd."
            ),
        ) from exc

    if in_use:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Dit CV wordt al gebruikt "
                "door een gegenereerde reactie "
                "en kan daarom niet worden "
                "verwijderd."
            ),
        )

    storage_path = (
        active_cv.get(
            "storage_path"
        )
    )

    if not isinstance(
        storage_path,
        str,
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Het CV heeft geen "
                "geldig opslagpad."
            ),
        )

    try:
        # Eerst het daadwerkelijke privébestand
        # verwijderen. Bij een DB-fout kan de
        # operatie daarna veilig opnieuw worden
        # geprobeerd.
        remove_user_cv_file(
            storage_path=(
                storage_path
            )
        )

        delete_user_cv_record(
            user_id=identity.id,
            cv_id=cv_id,
        )

    except Exception as exc:
        logger.exception(
            "Verwijderen van basis-CV "
            "is mislukt."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Het CV kon momenteel "
                "niet volledig worden verwijderd."
            ),
        ) from exc

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )