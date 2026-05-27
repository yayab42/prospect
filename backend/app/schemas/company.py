from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyBase(BaseModel):
    name: str = Field(max_length=255)
    siren: str | None = Field(default=None, max_length=9)
    siret: str | None = Field(default=None, max_length=14)
    address: str | None = Field(default=None, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=255)
    description: str | None = None
    data_source: str = Field(default="manual", max_length=50)

    @field_validator("name", "data_source")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be empty.")
        return value

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if len(value) != 9 or not value.isdigit():
            raise ValueError("SIREN must contain exactly 9 digits.")
        return value

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if len(value) != 14 or not value.isdigit():
            raise ValueError("SIRET must contain exactly 14 digits.")
        return value

    @field_validator("address", "postal_code", "city", "website", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    items: list[CompanyRead]
    total: int
    limit: int
    offset: int
