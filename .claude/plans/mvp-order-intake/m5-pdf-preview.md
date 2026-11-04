---
issue: M5
title: PDF preview pane on the review screen
branch: feat/dme-order-intake-p5-pdf-preview
status: cut
approved_by: Ernesto
approved_at: 2026-11-04
autonomy: pr
source: mvp
mvp: mvp-order-intake
size: S
est_tokens: 200000
est_lines: 250
shape: single
feature_branch: feat/dme-order-intake
base: feat/dme-order-intake
touches_api: false
tier: high
queue: false
---

# #M5 PDF preview pane on the review screen

## 1. Approval summary
**What:** `/orders/[id]` shows the stored PDF in a left pane with page navigation. Clicking a field's "p.N" evidence chip jumps the preview to that page.

**Why:** The human wants reviewers to check values against the source without leaving the screen (D11).

**How:**
- `react-pdf` (pdf.js) renders the PDF from a Blob, fetched with the bearer token from `GET /orders/{id}/document`
- the object URL is revoked on unmount
- two columns on ≥1024px; on smaller screens it stacks with a "Show document" toggle

Turned down: `<iframe src>` (can't send the auth header or control the page).

**Cut line:** if this milestone hasn't started by **14:30**, skip it. M6 then runs without it, and the release PR says so.

**Blast radius**
- Touches: web review screen only
- Files to touch:
  - `apps/web/components/pdf-preview.tsx`
  - `apps/web/app/orders/[id]/page.tsx`
  - `apps/web/components/issue-list.tsx`: page chip becomes a button
  - `apps/web/next.config.ts`: pdf.js worker, CSP `worker-src blob:`
  - `e2e/preview.spec.ts`
  - `apps/web/package.json`
- Also affected: none
- Left alone: the API
- Rollback: revert the PR

**Concerns:** Pin the pdf.js worker version to the `react-pdf` dependency, and serve the worker locally, not from a CDN (CSP).

**Security:** PDF bytes go only to the owner, held in memory as a Blob. Nothing new is stored.

**Acceptance criteria**
- **Preview** (AC-M5.1): on an uploaded order, the preview renders page 1 with an "N pages" count. Next/prev work.
- **Jump** (AC-M5.2): clicking the NPI's "p.1" chip shows page 1. On a multi-page synthetic case, clicking "p.3" shows page 3.
- **No document** (AC-M5.3): a manually created order shows no pane and no errors.
- **Audit** (AC-M5.4): UI audit has 0 serious findings. Screenshot of `/orders/[id]` at 1280 and 390.

**How it will be proven:** Playwright headless against local · UI audit

**Size** S · ~250 lines · ~200k tokens · single PR

**Out of scope:** highlighting the evidence text inside the PDF

**Context:** none

### Status: CUT at re-plan (13:50)
The 14:30 cut line falls inside wave 2, so this milestone isn't built for the assessment. It's backlog B9. The stored PDF remains available via `GET /orders/{id}/document` (M3b), so adding the pane later is web-only.

## 3. Design & architecture
Design source: `docs/context/designs/ui.md`, review wireframe (left pane).

## 4. Plan
### Tasks (one commit each, in order)
The builder commits after each task once its tests pass, with conventional messages:
1. `feat: add pdf preview component with page navigation`
2. `feat: link evidence page chips to the preview`
3. `feat: stack the preview on small screens`
4. `test: add preview playwright spec`

### Tests to add
- `e2e/preview.spec.ts`: AC-M5.1, AC-M5.2, AC-M5.3

### Screens
- `/orders/[id]`: adds the preview pane

## 5. Evidence
## 6. Retro
## 7. Hand-off
