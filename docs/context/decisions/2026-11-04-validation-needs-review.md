# ADR: Validate before saving and never guess; route problems to needs_review

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D7, D16)

## Context
R3: check extracted values before saving them, and don't guess when a field is missing. The benchmark fax contains an NPI that fails its checksum (9182734556) and a DOB that makes the patient 124 years old.

## Options
1. **Reject the upload (422) when any field is missing or invalid.** Loses the values that were read correctly, and the user re-keys everything.
2. **Save everything and leave it to the user.** Violates R3.
3. **Save as `needs_review` with per-field issues, and promote to `ready` only once every field passes.**

## Decision
Option 3. The same validators (`app/validation/`) run on extraction, on manual create and on every PATCH:

| Field | Error (blocks `ready`) | Warning (shown, doesn't block) |
|---|---|---|
| any | missing (null) → `not_found`; value missing from its evidence quote → `ungrounded` (value dropped) | — |
| names | empty, digits, over 100 characters | multiple candidates found |
| DOB | unparseable, in the future, before 1900-01-01 | age over 120 (the benchmark is 124) |
| NPI | not 10 digits, first digit not 1/2, fails the Luhn check with prefix 80840 | — |

A present-but-invalid value is stored **exactly as read** and flagged. It is never cleared or "fixed". `status = ready` iff all 5 fields are non-null and no error issues remain. Issues are recomputed on every write.

## Consequences
- The benchmark lands correctly in `needs_review` with `npi.checksum_failed`.
- NPPES registry verification (name ↔ NPI match) is in the backlog. It would add a third issue source.
