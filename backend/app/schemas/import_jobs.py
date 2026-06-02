from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportJobCreateResponse(BaseModel):
    id: UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


class ImportJobRead(BaseModel):
    id: UUID
    original_filename: str
    status: str
    imported_rows: int
    rejected_rows: int
    errors: list[dict] | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ImportJobProcessResponse(BaseModel):
    id: UUID
    status: str
    imported_rows: int
    rejected_rows: int
    errors: list[dict] | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)
