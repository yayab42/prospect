from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate


def create_company(db: Session, company_create: CompanyCreate) -> Company:
    company = Company(**company_create.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_company_by_id(db: Session, company_id: UUID) -> Company | None:
    return db.get(Company, company_id)


def list_companies(
    db: Session,
    q: str | None,
    city: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Company], int]:
    filters = []
    if city and city.strip():
        filters.append(Company.city.ilike(city.strip()))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(or_(Company.name.ilike(pattern), Company.siren.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(Company).where(*filters)) or 0
    statement = (
        select(Company)
        .where(*filters)
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(statement).all())
    return items, total
