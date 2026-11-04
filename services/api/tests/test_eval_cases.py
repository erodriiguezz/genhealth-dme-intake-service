"""AC-M3.6: the eval corpus (benchmark + synthetic cases) exists with the expected shape."""

import json
from pathlib import Path

import pypdf

CASES = Path(__file__).resolve().parents[3] / "evals" / "cases"


def test_ac_m3_6_cases_and_expected_json_match():
    expected = json.loads((CASES / "expected.json").read_text())
    assert len(expected) >= 7  # benchmark + at least 6 synthetic
    assert "genhealth-cpap-fax" in expected
    for name, exp in expected.items():
        pdf = CASES / f"{name}.pdf"
        assert pdf.exists(), name
        assert len(pypdf.PdfReader(str(pdf)).pages) == exp["pages"], name
        assert exp["expected_status"] in {"ready", "needs_review"}
