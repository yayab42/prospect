from typing import Annotated
from uuid import UUID
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.import_job_repository import get_import_job_by_id
from app.schemas.import_jobs import (
    ImportJobCreateResponse,
    ImportJobProcessResponse,
    ImportJobRead,
)
from app.services.csv_upload import (
    CSVFileTooLarge,
    UnsupportedCSVFile,
    read_csv_upload_file,
)
from app.services.import_job_orchestrator import (
    ImportJobOrchestrationError,
    create_company_import_job,
)
from app.services.import_job_processor import (
    ImportJobAlreadyProcessedError,
    ImportJobNotFoundError,
    process_company_import_job,
    ImportJobProcessingError,
)
from app.services.import_job_storage import (
    ImportFileStorageError,
    InvalidImportFileExtension,
)


router = APIRouter(prefix="/api/v1/import-jobs", tags=["import-jobs"])


def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    settings = get_settings()
    configured_token = settings.internal_api_token

    if configured_token is None or not configured_token.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal processing is not configured",
        )

    if x_internal_token is None or not secrets.compare_digest(
        x_internal_token,
        configured_token.get_secret_value(),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal token",
        )


@router.post(
    "/companies-csv",
    response_model=ImportJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_company_csv_import_job(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ImportJobCreateResponse:
    try:
        file_content = await read_csv_upload_file(file)
        job = create_company_import_job(
            db,
            file_content=file_content,
            original_filename=file.filename or "companies.csv",
        )
        return ImportJobCreateResponse.model_validate(job)
    except (UnsupportedCSVFile, InvalidImportFileExtension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        ) from None
    except CSVFileTooLarge:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV file is too large",
        ) from None
    except ImportFileStorageError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store import file",
        ) from None
    except ImportJobOrchestrationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Import orchestration is unavailable",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create import job",
        ) from None
    finally:
        await file.close()


@router.get("/{job_id}", response_model=ImportJobRead)
def get_company_import_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ImportJobRead:
    job = get_import_job_by_id(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    return ImportJobRead.model_validate(job)


@router.post(
    "/{job_id}/process",
    response_model=ImportJobProcessResponse,
    dependencies=[Depends(verify_internal_token)],
)
def process_company_csv_import_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ImportJobProcessResponse:
    try:
        return process_company_import_job(db, job_id)
    except ImportJobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        ) from None
    except ImportJobAlreadyProcessedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Import job is not pending",
        ) from None
    except ImportJobProcessingError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import job failed",
        ) from None
