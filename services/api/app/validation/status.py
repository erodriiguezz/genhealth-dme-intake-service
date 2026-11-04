from collections.abc import Iterable
from typing import Any

from app.validation import FIELDS
from app.validation.issue import Issue


def derive_status(values: dict[str, Any], issues: Iterable[Issue]) -> str:
    """ready iff all five fields are present and no error-severity issue remains."""
    complete = all(values.get(f) is not None for f in FIELDS)
    has_error = any(i.severity == "error" for i in issues)
    return "ready" if complete and not has_error else "needs_review"
