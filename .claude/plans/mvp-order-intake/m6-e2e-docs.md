---
issue: M6
title: End-to-end proof on the deployed app, README and review guide
branch: feat/order-intake-p6-e2e-docs
status: draft
approved_by:
approved_at:
autonomy: pr
source: mvp
mvp: mvp-order-intake
size: M
est_tokens: 250000
est_lines: 200
shape: single
feature_branch: feat/order-intake
base: feat/order-intake
touches_api: false
tier: high
queue: false
---

# #M6 End-to-end proof on the deployed app, README and review guide

## 1. Approval summary
**What:** The three agreed journeys pass headless against the **deployed** Vercel + Railway URLs (real Claude). The README gives graders everything: live URLs, the seeded reviewer logins (emails only), a curl walkthrough, local setup, architecture, the eval results and the process trail (`docs/process/`).

**Why:** R5 is the hard gate, and the graders' first experience is the README and the live URL.

**How:** `e2e/journeys.spec.ts` parameterized by `BASE_URL` and `API_URL`. Test users are created at runtime with random emails, so the run doesn't depend on the seeded passwords. Redeploy API and web from the feature-branch head first. Turned down: GitHub-triggered deploys (switched on after the release PR merges).

**Blast radius**
- Touches: tests and docs, plus a redeploy
- Files to touch:
  - `e2e/journeys.spec.ts`
  - `e2e/fixtures/`: the CPAP fax and the synthetic missing-DOB PDF, copied from `evals/cases`
  - `README.md`
  - `docs/reviews/mvp-order-intake.md`
  - `docs/context/status.md`
  - `docs/process/timeline.md`: final timestamps
- Also affected: none
- Left alone: app code (any failure found here goes to a fix in the owning area, within this PR, kept small)
- Rollback: n/a

**Concerns:** If `ANTHROPIC_API_KEY` or `SEED_USERS` aren't set in Railway yet, AC-M6.1/M6.3 can't pass on deployed. Record it as a Hand-off line for the human and keep going.

**Security:** No secrets in the README. Reviewer emails are listed, and passwords are sent separately by the human.

**Acceptance criteria**
- **Journey 1** (AC-M6.1): Sign up → upload the CPAP fax → order shows Marie / Curie / 1900-12-05 / Arjun Raj… / 9182734556 with "Fails NPI checksum" and `needs_review` → correct the NPI → Save → `ready`, on deployed.
- **Journey 2** (AC-M6.2): User B can't see user A's order in the list, and gets "Order not found" in the UI and 404 from the API for A's order and its PDF, on deployed.
- **Journey 3** (AC-M6.3): Upload the synthetic no-DOB PDF → DOB is empty with "Not found in document" and `needs_review`, with nothing invented, on deployed.
- **README** (AC-M6.4): a fresh clone following the README reaches green `make verify` and a running app, and the curl walkthrough (register → login → upload → get → patch → delete) works against the public API as written.

**How it will be proven:** Playwright headless against the deployed URLs · curl walkthrough executed against deployed · screenshots in the How to review

**Size** M · ~200 lines · ~250k tokens · single PR

**Out of scope:** CI, custom domain

**Context:** `status.md`, "Code", "Deploy" and "Plan" rows: final state

## 4. Plan
### Tasks (one commit each, in order)
The builder commits after each task once its tests pass, with conventional messages:
1. `test: add deployed journey specs`
2. `test: add deployed curl smoke script`
3. `docs: write readme with live urls and walkthrough`
4. `docs: add how-to-review guide and final status`

### Tests to add
- `e2e/journeys.spec.ts`: AC-M6.1, AC-M6.2, AC-M6.3 (`BASE_URL`/`API_URL` set to deployed)
- curl walkthrough script `scripts/smoke-deployed.sh`: AC-M6.4

### Context
| File | Row | Change |
| --- | --- | --- |
| status.md | Code, Deploy, Plan | Final state and URLs |

## 5. Evidence
## 6. Retro
## 7. Hand-off
