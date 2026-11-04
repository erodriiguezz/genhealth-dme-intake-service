from datetime import date

from app.validation.issue import Issue

FIELD = "patient_dob"
MIN_DOB = date(1900, 1, 1)
MAX_AGE = 120


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_dob(value: date | None, today: date) -> list[Issue]:
    if value is None:
        return [Issue(FIELD, "patient_dob.not_found", "error", "Not found. Enter it manually.")]
    if value > today:
        return [Issue(FIELD, "dob.in_future", "error", "Date of birth is in the future.")]
    if value < MIN_DOB:
        return [Issue(FIELD, "dob.too_old", "error", "Date of birth is before 1900-01-01.")]
    age = age_on(value, today)
    if age > MAX_AGE:
        return [
            Issue(
                FIELD,
                "dob.age_over_120",
                "warning",
                f"Patient would be {age} years old. Check the date.",
            )
        ]
    return []
