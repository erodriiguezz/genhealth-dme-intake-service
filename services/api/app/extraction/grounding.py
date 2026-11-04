"""Pure grounding checks over extraction output. No I/O."""

import re
from datetime import date, datetime

from .base import ExtractionResult, FieldResult

_WS = re.compile(r"\s+")
_NPI_SEP = re.compile(r"[\s\-.]+")
_DATE_SEP = re.compile(r"[\s\-./,]+")


def is_grounded(field: str, value: str | None, evidence: str | None) -> bool:
    """The value must appear in its evidence on digit (NPI, DOB) or word (names) boundaries."""
    if not value or not evidence:
        return False
    v, e = value.casefold(), evidence.casefold()
    if field == "provider_npi":
        v, e = _NPI_SEP.sub("", v), _NPI_SEP.sub("", e)
        return bool(v) and re.search(rf"(?<!\d){re.escape(v)}(?!\d)", e) is not None
    if field == "patient_dob":
        tokens = [t for t in _DATE_SEP.split(v) if t]
        if not tokens:
            return False
        if len(tokens) == 1 and v.isdigit():
            e = _DATE_SEP.sub("", e)
            return re.search(rf"(?<!\d){re.escape(v)}(?!\d)", e) is not None
        sep = r"[\s\-./,]+"
        pattern = sep.join(re.escape(t) for t in tokens)
        for m in re.finditer(rf"(?<!\w){pattern}(?!\w)", e):
            # a bigger date (e.g. 12/05/1900 around 05/1900) is not the same date
            if re.search(r"\d[\s\-./,]*$", e[: m.start()]) or re.match(
                r"[\s\-./,]*\d", e[m.end() :]
            ):
                continue
            return True
        return False
    v, e = _WS.sub(" ", v).strip(), _WS.sub(" ", e).strip()
    return bool(v) and re.search(rf"(?<!\w){re.escape(v)}(?!\w)", e) is not None


def _issue(field: str, code: str, severity: str, message: str) -> dict:
    return {
        "field": field,
        "code": code,
        "severity": severity,
        "message": message,
        "source": "extraction",
    }


def apply_grounding(result: ExtractionResult) -> tuple[dict[str, FieldResult], list[dict]]:
    """Return (fields with ungrounded values dropped, issues). The input is not mutated."""
    fields: dict[str, FieldResult] = {}
    issues: list[dict] = []
    for name, f in result.fields.items():
        if f.value is None or f.value == "":
            fields[name] = FieldResult()
            continue
        if is_grounded(name, f.value, f.evidence):
            fields[name] = f
        else:
            fields[name] = FieldResult(evidence=f.evidence, page=f.page)
            issues.append(
                _issue(
                    name,
                    f"{name}.ungrounded",
                    "error",
                    "Extracted value was not found in its evidence quote and was dropped.",
                )
            )
    names = {_WS.sub(" ", c.name).strip().casefold() for c in result.provider_candidates}
    if len(names) > 1:
        issues.append(
            _issue(
                "provider_name",
                "provider.multiple_candidates",
                "warning",
                "The document names more than one provider; confirm the ordering provider.",
            )
        )
    return fields, issues


_MONTHS = "%B %d, %Y"


def parse_dob(raw: str | None) -> date | None:
    """US MM/DD/YYYY first, then ISO, then 'Month D, YYYY'. Unparseable -> None."""
    if not raw:
        return None
    s = _WS.sub(" ", raw).strip()
    if m := re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s):
        try:
            return date(int(m[3]), int(m[1]), int(m[2]))
        except ValueError:
            return None
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s):
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    for fmt in (_MONTHS, "%b %d, %Y", "%B %d %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_npi(raw: str | None) -> str | None:
    if raw is None:
        return None
    return _NPI_SEP.sub("", raw) or None
