---
issue: M4
title: "Web workflow UI: auth, orders list, upload and review, manual CRUD"
branch: feat/dme-order-intake-p4-web-ui
status: draft
approved_by:
approved_at:
autonomy: pr
source: mvp
mvp: mvp-order-intake
size: L
est_tokens: 500000
est_lines: 800
shape: single
feature_branch: feat/dme-order-intake
base: feat/dme-order-intake
touches_api: false
tier: high
queue: false
---

# #M4 Web workflow UI: auth, orders list, upload and review, manual CRUD

## 1. Approval summary
**What:** The Next.js app covers the full workflow: sign up/in/out, the orders list, upload → extraction progress → review screen with per-field issues and evidence → fix → save → status updates, manual create/edit/delete. Every route has loading, empty and error states.

**Why:** The human chose a review UI. It makes R2/R3 visible, which is what intake staff actually use.

**How:**
- client components with a typed fetch wrapper generated from the API's OpenAPI (`openapi-typescript`)
- token in `sessionStorage`, an auth context, and a redirect to `/login` on 401
- shadcn/ui (button, input, form, table, badge, tabs, alert, alert-dialog, skeleton, sonner)
- react-hook-form + zod for field shape only. The server owns validity and status

The builder follows the `design` skill and `docs/context/designs/ui.md`. Turned down: server actions / a BFF (the 4.5 MB body limit; see the frontend ADR).

**Blast radius**
- Touches: web only
- Files to touch:
  - `apps/web/src/lib/{api.ts,api-types.ts,auth.tsx}`
  - `apps/web/src/app/{layout.tsx,page.tsx}`: `/` redirects to `/orders` or `/login`
  - `apps/web/src/app/(auth)/{login,signup}/page.tsx`
  - `apps/web/src/app/orders/{page.tsx,new/page.tsx,[id]/page.tsx}`
  - `apps/web/src/components/{order-form,issue-list,status-badge,upload-dropzone,orders-table,app-header,phi-banner}.tsx`
  - `apps/web/src/components/ui/*`: shadcn
  - `apps/web/next.config.ts`: CSP headers
  - `e2e/{auth,orders,upload}.spec.ts`
  - `apps/web/package.json`: `gen:api` script
- Also affected: none
- Left alone: the API (if it needs a change, write it up as a finding, don't make it)
- Rollback: revert the PR

**Concerns:** Local QA runs the API with `EXTRACTION_PROVIDER=fake`, so upload e2e is deterministic and free. The real extractor is proven on deployed in M6.

**Security:**
- Data in and out: JWT and PHI fields over HTTPS
- Who can access it: the signed-in owner
- Stored: the JWT in `sessionStorage` only
- Abuse: XSS → CSP, no `dangerouslySetInnerHTML`, no third-party scripts

**Acceptance criteria**
- **Auth** (AC-M4.1): sign up → lands on `/orders` (empty state shown). Logout → `/login`. Bad credentials show an inline error. Visiting `/orders` signed out redirects to `/login`.
- **Upload + review** (AC-M4.2): upload a PDF → progress state with elapsed seconds → `/orders/[id]` showing all 5 fields. The NPI shows "Fails NPI checksum" with `aria-invalid`. Each field shows its evidence quote and page chip. The status badge reads "Needs review".
- **Fix → ready** (AC-M4.3): correct the NPI and Save → the badge reads "Ready", the issue is gone, and the list shows Ready.
- **Manual CRUD** (AC-M4.4): create an order manually → appears in the list. Edit → persists after reload. Delete via the confirm dialog → gone from the list.
- **States** (AC-M4.5): list skeleton while loading. Upload errors (non-PDF, too big, 502) show inline with a retry. An unknown or foreign order id shows "Order not found".
- **Audit** (AC-M4.6): `.claude/design-review/ui-audit.json` has 0 serious findings. Screenshots of `/login`, `/orders` (empty and filled), `/orders/new`, `/orders/[id]` (needs review and ready) at 1280 and 390.

**How it will be proven:** Playwright headless against the local app (API in fake-extractor mode) · UI audit · screenshots

**Size** L · ~800 lines · ~500k tokens · single PR

**Out of scope:** the PDF preview pane (M5), dark-mode toggle (follows the system setting)

**Context:** none

---
## 3. Design & architecture
Design source: **the signed-off prototype** (Claude artifact https://claude.ai/artifact/SqXMdtrkFR3SBXVDuTwSM5, copy in `docs/context/designs/prototype/`: `Main.dc.html` flow, `States.dc.html` edge states) plus `docs/context/designs/ui.md`. Match its layout, copy, tokens and states. M4 can't start until the human has signed off the prototype (decision log). Fake mode: the API's `EXTRACTION_PROVIDER=fake` returns the benchmark values. It is only allowed when `ENV != production`, and the API refuses to start otherwise.

### Decisions
`2026-11-04-frontend-direct-api.md`

## 4. Plan
### Tasks (one commit each, in order)
The builder commits after each task once its tests pass, with conventional messages:
1. `feat: add typed api client generated from openapi`
2. `feat: add auth context, login and signup pages`
3. `feat: add app header, demo banner and route guard`
4. `feat: add orders list with filters and states`
5. `feat: add upload page with extraction progress and errors`
6. `feat: add review screen with issues and evidence`
7. `feat: add manual create, edit and delete flows`
8. `test: add playwright specs for auth, orders and upload`
9. `style: polish to the prototype and fix ui audit findings`

### Tests to add
- `e2e/auth.spec.ts`: AC-M4.1. `e2e/upload.spec.ts`: AC-M4.2, AC-M4.3, AC-M4.5. `e2e/orders.spec.ts`: AC-M4.4, AC-M4.5

### Screens
- `/login`, `/signup`, `/orders`, `/orders/new`, `/orders/[id]`

### Context
none

## 5. Evidence
## 6. Retro
## 7. Hand-off
