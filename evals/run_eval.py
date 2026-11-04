"""Run the configured extractor + grounding over evals/cases and score it.

Run: cd services/api && uv run python ../../evals/run_eval.py
Provider comes from EXTRACTION_PROVIDER (anthropic | fake). Writes
docs/evidence/extraction-eval.{json,md}. All case data is synthetic or the public benchmark.
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.extraction import ExtractionError, ExtractionNotConfigured, get_extractor  # noqa: E402
from app.extraction.base import FIELD_NAMES  # noqa: E402
from app.extraction.grounding import apply_grounding, normalize_npi, parse_dob  # noqa: E402

CASES = ROOT / "evals" / "cases"
OUT = ROOT / "docs" / "evidence"
PRICE_IN, PRICE_OUT = 4.0, 20.0  # USD per MTok


def _squash(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip().casefold()


def score_field(name: str, got: str | None, exp: dict) -> tuple[bool, bool]:
    """Return (correct, no_guess_violation)."""
    key = "provider_name_contains" if name == "provider_name" else name
    want = exp[key]
    if want is None:
        return got is None, got is not None
    if got is None:
        return False, False
    if name == "patient_dob":
        d = parse_dob(got)
        return d is not None and d.isoformat() == want, False
    if name == "provider_npi":
        return normalize_npi(got) == want, False
    if name == "provider_name":
        return _squash(want) in _squash(got), False
    return _squash(got) == _squash(want), False


def main() -> int:
    expected = json.loads((CASES / "expected.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        extractor = get_extractor()
    except ExtractionNotConfigured as e:
        msg = f"live eval not run: {e}"
        print(msg)
        (OUT / "extraction-eval.md").write_text(f"# Extraction eval\n\n{msg}\n")
        (OUT / "extraction-eval.json").write_text(
            json.dumps({"status": "not_run", "reason": str(e)}) + "\n"
        )
        return 3

    rows, case_out = [], {}
    tot = {"fields": 0, "correct": 0, "no_guess": 0, "in": 0, "out": 0, "errors": 0}
    provider = model = prompt_version = None
    for name, exp in expected.items():
        pdf = CASES / f"{name}.pdf"
        try:
            res = extractor.extract(pdf.read_bytes(), pdf.name)
        except (ExtractionError, ExtractionNotConfigured) as e:
            tot["errors"] += 1
            tot["fields"] += len(FIELD_NAMES)
            case_out[name] = {"error": str(e)}
            rows.append((name, "(all)", "ERROR", str(e)))
            continue
        provider, model, prompt_version = res.provider, res.model, res.prompt_version
        tot["in"] += res.input_tokens or 0
        tot["out"] += res.output_tokens or 0
        fields, issues = apply_grounding(res)
        per = {}
        for f in FIELD_NAMES:
            got = fields[f].value
            ok, ng = score_field(f, got, exp)
            tot["fields"] += 1
            tot["correct"] += ok
            tot["no_guess"] += ng
            per[f] = {"got": got, "ok": ok, "no_guess_violation": ng}
            rows.append((name, f, "PASS" if ok else ("NO-GUESS" if ng else "FAIL"), got))
        case_out[name] = {
            "fields": per,
            "issues": [i["code"] for i in issues],
            "latency_ms": res.latency_ms,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
        }

    acc = tot["correct"] / tot["fields"] if tot["fields"] else 0.0
    cost = (tot["in"] * PRICE_IN + tot["out"] * PRICE_OUT) / 1_000_000
    run_at = datetime.now(UTC).isoformat(timespec="seconds")
    summary = {
        "status": "run",
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "run_at": run_at,
        "cases": len(expected),
        "fields_scored": tot["fields"],
        "fields_correct": tot["correct"],
        "field_accuracy": round(acc, 4),
        "no_guess_violations": tot["no_guess"],
        "case_errors": tot["errors"],
        "input_tokens": tot["in"],
        "output_tokens": tot["out"],
        "cost_usd_estimate": round(cost, 4),
        "targets": {"field_accuracy": 0.95, "no_guess_violations": 0},
        "results": case_out,
    }
    (OUT / "extraction-eval.json").write_text(json.dumps(summary, indent=2) + "\n")

    md = ["# Extraction eval", ""]
    if provider == "fake":
        md += [
            "> Harness check with the FakeExtractor (returns the CPAP benchmark values for every",
            "> case), so only the benchmark case is expected to pass.",
            "> **Live eval not run: no key in worktree.**",
            "",
        ]
    md += [
        f"- Provider / model: `{provider}` / `{model}`",
        f"- Prompt version: `{prompt_version}`",
        f"- Run at: {run_at}",
        f"- Cases: {len(expected)} ({tot['errors']} errored)",
        f"- Field accuracy: **{acc:.1%}** ({tot['correct']}/{tot['fields']}), target >= 95%",
        f"- No-guess violations: **{tot['no_guess']}**, target 0",
        f"- Tokens in/out: {tot['in']} / {tot['out']}; cost estimate "
        f"${cost:.2f} at ${PRICE_IN:g}/${PRICE_OUT:g} per MTok",
        "",
        "| Case | Field | Result | Extracted |",
        "| --- | --- | --- | --- |",
    ]
    for case, field, result, got in rows:
        md.append(f"| {case} | {field} | {result} | {got if got else '(null)'} |")
    (OUT / "extraction-eval.md").write_text("\n".join(md) + "\n")
    print(
        f"{provider}: accuracy {acc:.1%}, no-guess violations {tot['no_guess']}, "
        f"errors {tot['errors']}, est cost ${cost:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
