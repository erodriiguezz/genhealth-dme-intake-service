from datetime import date

from app.extraction import ExtractionResult, FieldResult, ProviderCandidate
from app.extraction.grounding import apply_grounding, is_grounded, normalize_npi, parse_dob


def _result(fields, candidates=()):
    return ExtractionResult(
        provider="t",
        model="t",
        prompt_version="t",
        fields=fields,
        provider_candidates=list(candidates),
    )


def test_dob_separator_variants_grounded():
    assert is_grounded("patient_dob", "12/05/1900", "DOB 12-05-1900")
    assert is_grounded("patient_dob", "12/05/1900", "DOB: 12 05 1900")


def test_npi_with_spaces_grounded():
    assert is_grounded("provider_npi", "9182734556", "NPI: 9182 734 556")
    assert is_grounded("provider_npi", "9182-734-556", "NPI 9182734556")


def test_case_and_whitespace_normalized():
    assert is_grounded("patient_first_name", "marie", "Patient:  MARIE\n Curie")


def test_value_not_in_evidence_dropped_with_issue():
    r = _result(
        {"provider_npi": FieldResult(value="1234567893", evidence="NPI 9182734556", page=1)}
    )
    fields, issues = apply_grounding(r)
    assert fields["provider_npi"].value is None
    assert issues == [
        {
            "field": "provider_npi",
            "code": "provider_npi.ungrounded",
            "severity": "error",
            "message": issues[0]["message"],
            "source": "extraction",
        }
    ]


def test_missing_evidence_is_ungrounded():
    fields, issues = apply_grounding(_result({"patient_dob": FieldResult(value="01/01/1950")}))
    assert fields["patient_dob"].value is None
    assert issues[0]["code"] == "patient_dob.ungrounded"


def test_null_value_not_an_issue():
    fields, issues = apply_grounding(_result({"patient_dob": FieldResult()}))
    assert fields["patient_dob"].value is None and issues == []


def test_multiple_candidates_warning():
    cands = [ProviderCandidate(name="A B"), ProviderCandidate(name="C D", role="referring")]
    _, issues = apply_grounding(_result({}, cands))
    assert [i["code"] for i in issues] == ["provider.multiple_candidates"]
    assert issues[0]["severity"] == "warning"


def test_same_candidate_twice_no_warning():
    cands = [ProviderCandidate(name="A  B"), ProviderCandidate(name="a b", page=2)]
    assert apply_grounding(_result({}, cands))[1] == []


def test_parse_dob_formats():
    assert parse_dob("12/05/1900") == date(1900, 12, 5)
    assert parse_dob("12-05-1900") == date(1900, 12, 5)
    assert parse_dob("1900-12-05") == date(1900, 12, 5)
    assert parse_dob("December 5, 1900") == date(1900, 12, 5)
    assert parse_dob("13/45/1900") is None
    assert parse_dob("sometime") is None
    assert parse_dob(None) is None


def test_normalize_npi():
    assert normalize_npi("9182 734-556.") == "9182734556"
    assert normalize_npi("91827/34556") == "91827/34556"
    assert normalize_npi(None) is None
