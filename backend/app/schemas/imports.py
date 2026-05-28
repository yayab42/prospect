from pydantic import BaseModel


class ImportRowError(BaseModel):
    line: int
    reason: str


class CompanyImportResponse(BaseModel):
    status: str
    imported_rows: int
    rejected_rows: int
    errors: list[ImportRowError]
