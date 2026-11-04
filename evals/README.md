# Extraction eval

Scores the configured extractor (plus the grounding check) on `evals/cases/`:
the GenHealth CPAP benchmark fax and 8 synthetic cases (all fake data).

```
make eval                              # live: needs ANTHROPIC_API_KEY in the API's local env file (~$1/run)
EXTRACTION_PROVIDER=fake make eval     # harness check, no API call
cd services/api && uv run python ../../evals/generate_cases.py   # regenerate synthetic PDFs
```

Output: `docs/evidence/extraction-eval.{json,md}`.

- `expected.json`: per case, expected values (`null` = must not be extracted),
  `provider_name_contains` for the ordering provider, and page count.
- Scoring: per-field normalized exact match (DOB compared as a parsed date, NPI with
  separators stripped, provider by contains-match). A **no-guess violation** is a non-null
  value where the expected value is null.
- Targets: >= 95% field accuracy, 0 no-guess violations.
- Exit code 3 and a "live eval not run" note when no API key is configured.
