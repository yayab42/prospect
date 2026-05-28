from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.imports import CompanyImportResponse
from app.services.company_import import InvalidCSVFile, import_companies_from_csv
from app.services.csv_upload import (
    CSVFileTooLarge,
    UnsupportedCSVFile,
    read_csv_upload_file,
)

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/companies-csv", response_model=CompanyImportResponse)
async def import_companies_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> CompanyImportResponse:
    try:
        file_content = await read_csv_upload_file(file)
        return import_companies_from_csv(db, file_content)
    except UnsupportedCSVFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        ) from None
    except CSVFileTooLarge:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV file is too large",
        ) from None
    except InvalidCSVFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file",
        ) from None
    finally:
        await file.close()
