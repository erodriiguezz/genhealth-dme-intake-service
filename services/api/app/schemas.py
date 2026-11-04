import re
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.validation.names import normalize_name

EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NPI_SEPARATORS = re.compile(r"[\s.\-]")


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_shape(cls, v: str) -> str:
        v = v.strip()
        if not EMAIL_SHAPE.match(v) or len(v) > 254:
            raise ValueError("not a valid email address")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class IssueOut(BaseModel):
    field: str
    code: str
    severity: Literal["error", "warning"]
    message: str
    source: Literal["validation", "extraction"]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    page_count: int
    size_bytes: int


class OrderFields(BaseModel):
    """Client-writable fields. extra=forbid keeps status, owner_id, issues, extraction out."""

    model_config = ConfigDict(extra="forbid")

    patient_first_name: str | None = Field(default=None, max_length=200)
    patient_last_name: str | None = Field(default=None, max_length=200)
    patient_dob: date | None = None
    provider_name: str | None = Field(default=None, max_length=300)
    provider_npi: str | None = Field(default=None, max_length=40)

    @field_validator("patient_first_name", "patient_last_name", "provider_name")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        return normalize_name(v)

    @field_validator("provider_npi")
    @classmethod
    def clean_npi(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = NPI_SEPARATORS.sub("", v)
        if len(v) > 20:
            raise ValueError("at most 20 characters")
        return v or None


class OrderCreate(OrderFields):
    pass


class OrderUpdate(OrderFields):
    pass


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: Literal["needs_review", "ready"]
    patient_first_name: str | None
    patient_last_name: str | None
    patient_dob: date | None
    provider_name: str | None
    provider_npi: str | None
    issues: list[IssueOut]
    document: DocumentOut | None
    created_at: datetime
    updated_at: datetime


class OrderOut(OrderSummary):
    extraction: dict[str, Any] | None


class OrderList(BaseModel):
    items: list[OrderSummary]
    total: int
