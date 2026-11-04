# ADR: Extract order fields with Claude reading the PDF natively

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D5, D6)

## Context
R2: extract the patient's first/last name and DOB, plus the ordering provider's name and NPI, from PDFs the system has never seen, including scanned faxes and messy multi-page documents. A wrong value means a denied claim.

## Options
1. **Claude API, native PDF input (each page as text + image), structured JSON output.** Reads scans, handwriting and odd layouts, and copes with distractors (referring vs. ordering physician). It costs about $0.09 per 5-page doc on Opus 5.5, takes 10–60s, and needs a third-party API (see the HIPAA ADR).
2. **Tesseract OCR, then an LLM on the text.** Cheaper tokens, but OCR errors on faxes carry into extraction, and layout and visual cues are lost.
3. **OCR + regex/heuristics.** Deterministic and free. Breaks on layouts it hasn't seen, which is exactly what the graders test.

## Decision
Option 1, behind an `Extractor` protocol (`services/api/app/extraction/`) with an `AnthropicExtractor` implementation. The default model is `claude-opus-5-5`, set by `EXTRACTION_MODEL`, with adaptive thinking and effort `high`. Output is constrained by a JSON schema: for each field `{value | null, evidence (verbatim quote), page}`, plus `candidates` when the document names more than one possible ordering provider.

The prompt rules:
- The ordering provider is the prescriber who signs the order, not the referring physician unless they are the same person.
- Return null when a value isn't stated explicitly. Never infer or normalize a value that isn't on the page.

A **grounding check** rejects any value whose evidence quote doesn't contain it. Server-side refusal fallback (`fallbacks: "default"`) is enabled.

## Consequences
- Accuracy is measured, not assumed: the `evals/` harness scores the GenHealth CPAP fax plus synthetic cases.
- Bedrock (AWS BAA) is a new `Extractor` implementation plus config, with no change to callers.
- Latency drives the synchronous-request ADR. Cost per doc is logged in the extraction metadata.
