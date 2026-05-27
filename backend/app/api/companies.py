from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company import Company
from app.repositories.company_repository import (
    create_company,
    get_company_by_id,
    list_companies,
)
from app.schemas.company import CompanyCreate, CompanyListResponse, CompanyRead


router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("", response_model=CompanyListResponse)
def read_companies(
    q: str | None = None,
    city: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CompanyListResponse:
    items, total = list_companies(db, q=q, city=city, limit=limit, offset=offset)
    return CompanyListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def add_company(
    company_create: CompanyCreate, db: Session = Depends(get_db)
) -> Company:
    try:
        return create_company(db, company_create)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A company with this SIREN or SIRET already exists.",
        ) from None


@router.get("/{company_id}", response_model=CompanyRead)
def read_company(company_id: UUID, db: Session = Depends(get_db)) -> Company:
    company = get_company_by_id(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found."
        )
    return company
