"""Pure validators. No I/O, no database: shared by manual CRUD and extraction."""

from datetime import date
from typing import Any

from app.validation.dob import validate_dob
from app.validation.issue import Issue
from app.validation.names import validate_name
from app.validation.npi import validate_npi

__all__ = ["FIELDS", "Issue", "validate_order"]

FIELDS = (
    "patient_first_name",
    "patient_last_name",
    "patient_dob",
    "provider_name",
    "provider_npi",
)


def validate_order(values: dict[str, Any], today: date | None = None) -> list[Issue]:
    """Run every field validator over the five order fields."""
    today = today or date.today()
    return [
        *validate_name("patient_first_name", values.get("patient_first_name"), 100),
        *validate_name("patient_last_name", values.get("patient_last_name"), 100),
        *validate_dob(values.get("patient_dob"), today),
        *validate_name("provider_name", values.get("provider_name"), 150, check_chars=False),
        *validate_npi(values.get("provider_npi")),
    ]
