from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_job import (
    IMPORT_JOB_STATUS_COMPLETED,
    IMPORT_JOB_STATUS_FAILED,
    IMPORT_JOB_STATUS_PENDING,
    IMPORT_JOB_STATUS_RUNNING,
    ImportJob,
)


def create_import_job(
    db: Session,
    original_filename: str,
    stored_filename: str,
) -> ImportJob:
    job = ImportJob(
        original_filename=original_filename,
        stored_filename=stored_filename,
        status=IMPORT_JOB_STATUS_PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_import_job_by_id(db: Session, job_id: UUID) -> ImportJob | None:
    return db.get(ImportJob, job_id)


def get_import_job_for_update(db: Session, job_id: UUID) -> ImportJob | None:
    statement = select(ImportJob).where(ImportJob.id == job_id).with_for_update()
    return db.scalar(statement)


def mark_import_job_running(db: Session, job: ImportJob) -> ImportJob:
    job.status = IMPORT_JOB_STATUS_RUNNING
    job.started_at = datetime.now(UTC)
    job.updated_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_import_job_completed(
    db: Session,
    job: ImportJob,
    imported_rows: int,
    rejected_rows: int,
    errors: list[dict] | None,
) -> ImportJob:
    now = datetime.now(UTC)
    job.status = IMPORT_JOB_STATUS_COMPLETED
    job.imported_rows = imported_rows
    job.rejected_rows = rejected_rows
    job.errors = errors
    job.error_message = None
    job.completed_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_import_job_failed(
    db: Session,
    job: ImportJob,
    error_message: str,
) -> ImportJob:
    now = datetime.now(UTC)
    job.status = IMPORT_JOB_STATUS_FAILED
    job.error_message = error_message
    job.completed_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
