from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.company_repository import create_company, list_companies
from app.schemas.company import CompanyCreate
from app.services.company_import import InvalidCSVFile, import_companies_from_csv
from app.services.csv_upload import (
    CSVFileTooLarge,
    UnsupportedCSVFile,
    read_csv_upload_file,
)


router = APIRouter(prefix="/web", tags=["web"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def render_companies_page(
    request: Request,
    db: Session,
    error: str | None = None,
    message: str | None = None,
    import_errors: list[str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    companies, _ = list_companies(db, q=None, city=None, limit=100, offset=0)
    return templates.TemplateResponse(
        request=request,
        name="companies.html",
        context={
            "companies": companies,
            "error": error,
            "message": message,
            "import_errors": import_errors or [],
        },
        status_code=status_code,
    )


def redirect_to_companies(**params: str | list[str]) -> RedirectResponse:
    url = "/web/companies"
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"

    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/companies", response_class=HTMLResponse)
def companies_page(
    request: Request,
    message: str | None = Query(default=None),
    error: str | None = Query(default=None),
    import_errors: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    return render_companies_page(
        request,
        db,
        error=error,
        message=message,
        import_errors=import_errors,
    )


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

    return redirect_to_companies()


@router.post("/imports/companies-csv", response_class=RedirectResponse, response_model=None)
async def import_companies_csv_web(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        file_content = await read_csv_upload_file(file)
        result = import_companies_from_csv(db, file_content)

        params: dict[str, str | list[str]] = {
            "message": (
                "Import completed: "
                f"{result.imported_rows} imported, {result.rejected_rows} rejected."
            )
        }

        if result.errors:
            params["import_errors"] = [
                f"Line {row_error.line}: {row_error.reason}"
                for row_error in result.errors
            ]

        return redirect_to_companies(**params)
    except UnsupportedCSVFile:
        return redirect_to_companies(error="Only CSV files are supported.")
    except CSVFileTooLarge:
        return redirect_to_companies(error="CSV file is too large.")
    except InvalidCSVFile:
        return redirect_to_companies(error="Invalid CSV file.")
    finally:
        await file.close()
