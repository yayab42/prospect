from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.company_repository import create_company, list_companies
from app.schemas.company import CompanyCreate


router = APIRouter(prefix="/web", tags=["web"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def render_companies_page(
    request: Request, db: Session, error: str | None = None, status_code: int = 200
) -> HTMLResponse:
    companies, _ = list_companies(db, q=None, city=None, limit=100, offset=0)
    return templates.TemplateResponse(
        request=request,
        name="companies.html",
        context={"companies": companies, "error": error},
        status_code=status_code,
    )


@router.get("/companies", response_class=HTMLResponse)
def companies_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return render_companies_page(request, db)


@router.post("/companies", response_class=RedirectResponse, response_model=None)
def submit_company(
    request: Request,
    name: str = Form(...),
    siren: str | None = Form(default=None),
    siret: str | None = Form(default=None),
    city: str | None = Form(default=None),
    postal_code: str | None = Form(default=None),
    website: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    try:
        company_create = CompanyCreate(
            name=name,
            siren=siren,
            siret=siret,
            city=city,
            postal_code=postal_code,
            website=website,
        )
        create_company(db, company_create)
    except ValidationError:
        return render_companies_page(
            request, db, error="Please enter valid company information.", status_code=422
        )
    except IntegrityError:
        db.rollback()
        return render_companies_page(
            request,
            db,
            error="A company with this SIREN or SIRET already exists.",
            status_code=409,
        )

    return RedirectResponse(url="/web/companies", status_code=status.HTTP_303_SEE_OTHER)
