from app.validation.issue import Issue

FIELD = "provider_npi"
NPI_PREFIX = "80840"  # ISO issuer prefix for US healthcare, prepended before the Luhn check


def luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_npi(value: str | None) -> list[Issue]:
    if value is None:
        return [Issue(FIELD, "provider_npi.not_found", "error", "Not found. Enter it manually.")]
    if len(value) != 10 or not (value.isascii() and value.isdigit()):
        return [Issue(FIELD, "npi.format", "error", "An NPI is exactly 10 digits.")]
    issues: list[Issue] = []
    if value[0] not in "12":
        issues.append(Issue(FIELD, "npi.prefix", "error", "An NPI starts with 1 or 2."))
    if not luhn_valid(NPI_PREFIX + value):
        issues.append(
            Issue(
                FIELD,
                "npi.checksum_failed",
                "error",
                "Fails the NPI checksum. This isn't a valid NPI as written.",
            )
        )
    return issues
