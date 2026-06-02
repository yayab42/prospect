from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.import_job import ImportJob
from app.repositories.import_job_repository import (
    create_import_job,
    mark_import_job_failed,
)
from app.services.import_job_storage import clean_original_filename, store_import_file


class ImportJobOrchestrationError(RuntimeError):
    pass


def trigger_company_import_job(job_id: UUID) -> None:
    settings = get_settings()
    webhook_url = settings.kestra_import_webhook_url

    if not webhook_url:
        raise ImportJobOrchestrationError("Import orchestration is not configured")

    try:
        response = httpx.post(
            webhook_url,
            json={"job_id": str(job_id)},
            timeout=5,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ImportJobOrchestrationError("Unable to trigger import orchestration") from exc


def create_company_import_job(
    db: Session,
    file_content: bytes,
    original_filename: str,
) -> ImportJob:
    stored_filename, _ = store_import_file(
        file_content=file_content,
        original_filename=original_filename,
    )
    safe_original_filename = clean_original_filename(original_filename)
    job = create_import_job(
        db,
        original_filename=safe_original_filename,
        stored_filename=stored_filename,
    )

    try:
        trigger_company_import_job(job.id)
    except ImportJobOrchestrationError:
        mark_import_job_failed(
            db,
            job,
            error_message="Import orchestration is unavailable",
        )
        raise

    return job
