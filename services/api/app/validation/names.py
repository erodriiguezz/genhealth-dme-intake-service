import re
import unicodedata

from app.validation.issue import Issue

_WS = re.compile(r"\s+")
# Letters (incl. accented), combining marks, space, apostrophes, hyphen, period, comma.
_ALLOWED = re.compile(r"^[^\W\d_]+(?:[^\W\d_]|[\s'’.,\-]|̀-ͯ)*$")


def normalize_name(value: str | None) -> str | None:
    """Trim and collapse whitespace. Empty becomes None (missing), never a guess."""
    if value is None:
        return None
    return _WS.sub(" ", value).strip() or None


def validate_name(
    field: str, value: str | None, max_len: int, check_chars: bool = True
) -> list[Issue]:
    if value is None:
        return [Issue(field, f"{field}.not_found", "error", "Not found. Enter it manually.")]
    issues: list[Issue] = []
    if check_chars and not _valid_chars(value):
        issues.append(
            Issue(field, "name.invalid_chars", "error", "Contains digits or unexpected symbols.")
        )
    if len(value) > max_len:
        issues.append(Issue(field, "name.too_long", "error", f"Longer than {max_len} characters."))
    return issues


# Letters (incl. accented), combining marks, space, apostrophes, hyphen, period, comma.
def _valid_chars(value: str) -> bool:
    return all(c.isalpha() or c in " '’.,-" or _is_mark(c) for c in value)


def _is_mark(c: str) -> bool:
    return unicodedata.category(c).startswith("M")
