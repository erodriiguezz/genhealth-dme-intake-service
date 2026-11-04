from datetime import date

import pytest

from app.validation import validate_order
from app.validation.dob import validate_dob
from app.validation.names import normalize_name, validate_name
from app.validation.npi import validate_npi

TODAY = date(2026, 11, 4)


def codes(issues):
    return [i.code for i in issues]


@pytest.mark.parametrize(
    ("npi", "expected"),
    [
        ("1234567893", []),
        ("1234567894", ["npi.checksum_failed"]),
        ("9182734556", ["npi.prefix", "npi.checksum_failed"]),
        ("123456789", ["npi.format"]),
        ("12345678933", ["npi.format"]),
        ("12345abcde", ["npi.format"]),
        ("3234567893", ["npi.prefix", "npi.checksum_failed"]),
        (None, ["provider_npi.not_found"]),
    ],
)
def test_npi_table(npi, expected):
    """AC-M2.4: Luhn table."""
    got = codes(validate_npi(npi))
    assert got == expected


def test_npi_leading_three_flags_prefix_only_when_checksum_ok():
    # 3 + 9 digits whose Luhn is valid: find one.
    from app.validation.npi import luhn_valid

    n = next(
        f"3{i:08d}{d}" for i in range(1000) for d in range(10) if luhn_valid(f"808403{i:08d}{d}")
    )
    assert codes(validate_npi(n)) == ["npi.prefix"]


def test_benchmark_npi_fails_checksum():
    issues = validate_npi("9182734556")
    assert "npi.checksum_failed" in codes(issues)
    assert all(i.severity == "error" for i in issues)


def test_dob_future_is_error():
    (i,) = validate_dob(date(2027, 1, 1), TODAY)
    assert (i.code, i.severity) == ("dob.in_future", "error")


def test_dob_before_1900_is_error():
    (i,) = validate_dob(date(1899, 12, 31), TODAY)
    assert (i.code, i.severity) == ("dob.too_old", "error")


def test_dob_1900_is_warning_not_error():
    (i,) = validate_dob(date(1900, 12, 5), TODAY)
    assert (i.code, i.severity) == ("dob.age_over_120", "warning")


def test_dob_ok_and_missing():
    assert validate_dob(date(1961, 3, 14), TODAY) == []
    assert codes(validate_dob(None, TODAY)) == ["patient_dob.not_found"]


def test_dob_age_boundary():
    assert validate_dob(date(1905, 11, 5), TODAY) == []  # turns 121 tomorrow
    assert codes(validate_dob(date(1905, 11, 4), TODAY)) == ["dob.age_over_120"]


def test_names():
    assert validate_name("patient_first_name", "Marie-Ève O'Brien Jr.", 100) == []
    assert codes(validate_name("patient_first_name", "Mar1e", 100)) == ["name.invalid_chars"]
    assert codes(validate_name("patient_last_name", "a" * 101, 100)) == ["name.too_long"]
    assert validate_name("provider_name", "a" * 150, 150, check_chars=False) == []
    assert validate_name("provider_name", "Ann Lee MD, 2nd", 150, check_chars=False) == []
    assert codes(validate_name("provider_name", None, 150)) == ["provider_name.not_found"]


def test_normalize_name():
    assert normalize_name("  Marie \t  Curie ") == "Marie Curie"
    assert normalize_name("   ") is None
    assert normalize_name(None) is None


def test_validate_order_all_missing():
    got = codes(validate_order({}, TODAY))
    assert got == [
        "patient_first_name.not_found",
        "patient_last_name.not_found",
        "patient_dob.not_found",
        "provider_name.not_found",
        "provider_npi.not_found",
    ]
