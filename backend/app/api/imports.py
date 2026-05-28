from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.imports import CompanyImportResponse
from app.services.company_import import InvalidCSVFile, import_companies_from_csv


MAX_CSV_SIZE_BYTES = 1024 * 1024

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/companies-csv", response_model=CompanyImportResponse)
async def import_companies_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> CompanyImportResponse:
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    file_content = await file.read(MAX_CSV_SIZE_BYTES + 1)

    if len(file_content) > MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV file is too large",
        )

    try:
        return import_companies_from_csv(db, file_content)
    except InvalidCSVFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file",
        ) from None
    finally:
        await file.close()