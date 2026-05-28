import csv
from io import StringIO

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.company_repository import create_company
from app.schemas.company import CompanyCreate
from app.schemas.imports import CompanyImportResponse, ImportRowError


ACCEPTED_COLUMNS = {
    "name",
    "siren",
    "siret",
    "address",
    "postal_code",
    "city",
    "website",
    "description",
    "data_source",
}

REQUIRED_COLUMNS = {"name"}
MAX_REPORTED_ERRORS = 100


class InvalidCSVFile(ValueError):
    pass


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


def _normalize_row(row: dict[str | None, str | None]) -> dict[str, str | None]:
    normalized_row: dict[str, str | None] = {}

    for key, value in row.items():
        if key is None:
            continue

        normalized_key = key.strip()
        if not normalized_key:
            continue

        normalized_row[normalized_key] = value

    return normalized_row


def _append_error(
    errors: list[ImportRowError],
    line: int,
    reason: str,
) -> None:
    if len(errors) >= MAX_REPORTED_ERRORS:
        return

    errors.append(ImportRowError(line=line, reason=reason))


def _build_company_payload(row: dict[str, str | None]) -> dict[str, str | None]:
    payload = {
        column: _normalize_value(row.get(column))
        for column in ACCEPTED_COLUMNS
        if column != "data_source"
    }

    data_source = _normalize_value(row.get("data_source"))
    payload["data_source"] = data_source or "csv"

    return payload


def _validation_reason(payload: dict[str, str | None]) -> str | None:
    if not payload.get("name"):
        return "Missing name"

    siren = payload.get("siren")
    if siren is not None and (len(siren) != 9 or not siren.isdigit()):
        return "Invalid SIREN"

    siret = payload.get("siret")
    if siret is not None and (len(siret) != 14 or not siret.isdigit()):
        return "Invalid SIRET"

    return None


def _validate_csv_headers(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise InvalidCSVFile("Invalid CSV file")

    normalized_fieldnames = {
        field.strip()
        for field in fieldnames
        if field is not None and field.strip()
    }

    if not REQUIRED_COLUMNS.issubset(normalized_fieldnames):
        raise InvalidCSVFile("Invalid CSV file")


def import_companies_from_csv(
    db: Session,
    file_content: bytes,
) -> CompanyImportResponse:
    try:
        csv_text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidCSVFile("Invalid CSV file") from exc

    if not csv_text.strip():
        raise InvalidCSVFile("Invalid CSV file")

    if "\x00" in csv_text:
        raise InvalidCSVFile("Invalid CSV file")

    imported_rows = 0
    rejected_rows = 0
    errors: list[ImportRowError] = []

    try:
        reader = csv.DictReader(StringIO(csv_text))
        _validate_csv_headers(reader.fieldnames)

        for row in reader:
            line_number = reader.line_num
            normalized_row = _normalize_row(row)
            payload = _build_company_payload(normalized_row)

            reason = _validation_reason(payload)
            if reason is not None:
                rejected_rows += 1
                _append_error(errors, line=line_number, reason=reason)
                continue

            try:
                company_create = CompanyCreate(**payload)
            except ValidationError:
                rejected_rows += 1
                _append_error(
                    errors,
                    line=line_number,
                    reason="Invalid company data",
                )
                continue

            try:
                create_company(db, company_create)
                imported_rows += 1
            except IntegrityError:
                db.rollback()
                rejected_rows += 1
                _append_error(
                    errors,
                    line=line_number,
                    reason="Company already exists",
                )
            except SQLAlchemyError:
                db.rollback()
                rejected_rows += 1
                _append_error(
                    errors,
                    line=line_number,
                    reason="Database error",
                )
    except csv.Error as exc:
        raise InvalidCSVFile("Invalid CSV file") from exc

    return CompanyImportResponse(
        status="completed",
        imported_rows=imported_rows,
        rejected_rows=rejected_rows,
        errors=errors,
    )