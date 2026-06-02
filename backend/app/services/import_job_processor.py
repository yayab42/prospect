from uuid import UUID

from sqlalchemy.orm import Session

from app.models.import_job import IMPORT_JOB_STATUS_PENDING
from app.repositories.import_job_repository import (
    get_import_job_by_id,
    get_import_job_for_update,
    mark_import_job_completed,
    mark_import_job_failed,
    mark_import_job_running,
)
from app.schemas.import_jobs import ImportJobProcessResponse
from app.services.company_import import import_companies_from_csv
from app.services.import_job_storage import get_import_file_path


class ImportJobNotFoundError(ValueError):
    pass


class ImportJobAlreadyProcessedError(ValueError):
    pass


class ImportJobProcessingError(RuntimeError):
    pass


def process_company_import_job(
        db: Session,
        job_id: UUID,
) -> ImportJobProcessResponse:
    job = get_import_job_for_update(db, job_id)

    if job is None:
        raise ImportJobNotFoundError("Import job not found")

    if job.status != IMPORT_JOB_STATUS_PENDING:
        db.rollback()
        raise ImportJobAlreadyProcessedError("Import job is not pending")

    job = mark_import_job_running(db, job)

    try:
        file_path = get_import_file_path(job.stored_filename)
        file_content = file_path.read_bytes()
        import_result = import_companies_from_csv(db, file_content)
        errors = [row_error.model_dump() for row_error in import_result.errors]

        job = get_import_job_by_id(db, job_id)
        if job is None:
            raise ImportJobNotFoundError("Import job not found")

        job = mark_import_job_completed(
            db,
            job,
            imported_rows=import_result.imported_rows,
            rejected_rows=import_result.rejected_rows,
            errors=errors,
        )

        return ImportJobProcessResponse.model_validate(job)

    except Exception as exc:
        db.rollback()

        job = get_import_job_by_id(db, job_id)
        if job is None:
            raise ImportJobNotFoundError("Import job not found") from None

        mark_import_job_failed(
            db,
            job,
            error_message="Import job failed",
        )

        raise ImportJobProcessingError("Import job failed") from exc
