# Grill log

The planning agent questions the human before any design is fixed. Each entry records the question, the options offered (the agent's recommendation is marked ★), the answer, and any pushback. The answers feed the MVP plan's Grill table and the ADRs.

## Opening observations (agent, 2026-11-04)

- Grading weight sits on R2 (unseen scanned faxes) and R5 (a public upload endpoint is a hard gate), so most of the effort goes there.
- The 3-hour timebox (R9) is tight for a monorepo, a frontend and two deploys. The frontend is optional per the brief, so it stays thin.
- Running the Python API on Vercel serverless was rejected up front: its 4.5 MB request-body limit breaks multi-page scanned PDFs.

## Round 1

_Asked 2026-11-04. Attempt 1: the human paused it to set up this log first. Attempt 2: the human asked to clarify the questions before answering. Attempt 3 (after the HIPAA answer): the human asked to clarify again._

**Clarification from the human:** "This might include HIPAA-regulated content. Is a direct Claude parser safe?"

**Agent's answer:** Only under a BAA. The same is true of every vendor that touches PHI, not just the LLM:
- Sending PHI to any third party (an LLM API, hosting, a database) requires a Business Associate Agreement with that vendor. Using Tesseract alone doesn't solve this, because the API host and the database still store PHI.
- Anthropic offers BAAs for its API to eligible customers (with zero data retention). Claude is also available through AWS Bedrock and Google Vertex AI, which are HIPAA-eligible services under those clouds' BAAs. Current terms must be confirmed before handling real PHI; the agent did not verify them in this session.
- For the take-home: only synthetic or sample PDFs. The code is built PHI-ready: the LLM provider sits behind an interface (Anthropic API today, Bedrock is a config swap), PDFs aren't kept after extraction, no PHI in logs, TLS everywhere, and a HIPAA posture ADR lists the BAAs production would need (LLM, API host, DB, frontend host).

**Clarification from the human:** "I'm leaning toward option 1 (Anthropic API, swappable). Can it be deployed today, cheaply?"

**Agent's answer:** Yes. Prices are Anthropic list prices as of 2026-10; page tokens are an estimate, at about 1.5–3k tokens per PDF page because each page goes in as text plus an image:

| Model | $/1M in / out | ~5-page scanned fax | 100 test uploads |
|-------|---------------|---------------------|------------------|
| Claude Opus 5.5 | $4 / $20 | ~$0.09 | ~$9 |
| Claude Sonnet 5.5 | $2 / $10 | ~$0.045 | ~$4.50 |
| Claude Haiku 5.5 | $0.10 / $0.50 | ~$0.002 | ~$0.20 |

Hosting: Vercel Hobby is $0, Neon free is $0, and Render is $0 on the free tier (cold starts) or $7/mo on Starter. The API key lives only in Render's environment settings, entered by the human; the agent never sees it. The API caps requests at 32 MB and 600 pages, which covers any realistic fax.

| # | Topic | Question | Options (★ = recommended) | Answer |
|---|-------|----------|---------------------------|--------|
| 1.1 | Extraction | How should the API extract the 5 fields from unseen PDFs (HIPAA-aware)? | ★ Anthropic API with native PDF input + structured output + deterministic validators, behind a swappable provider interface · Claude via AWS Bedrock now · Local OCR + regex | **Anthropic API, swappable** (after the HIPAA and cost clarifications above) |
| 1.1b | Model | Default extraction model (env var)? | ★ Opus 5.5 · Sonnet 5.5 · Haiku 5.5 | **Opus 5.5** |
| 1.2 | Missing data | What happens when a field is missing or fails validation? | ★ Save as `needs_review` with the field null + issues list, editable, `ready` only once all fields validate · Reject upload with 422 | **Save as needs_review** |
| 1.3 | Auth | How do users authenticate? | ★ API-owned email/password (argon2) + JWT, every query scoped by owner, cross-user → 404 · Clerk · Supabase Auth | **API-owned JWT** |
| 1.4 | Hosting | Where is it deployed? | ★ Vercel + Render Starter + Neon · Vercel + Render free + Neon · Vercel + Railway | **Vercel + Railway** (the human overrode the recommendation; Railway runs the API and Postgres in one project) |

## Round 2

_Asked 2026-11-04, 12:2x._

| # | Topic | Question | Options (★ = recommended) | Answer |
|---|-------|----------|---------------------------|--------|
| 2.1 | Timebox | Has the 3-hour timebox started? | ★ Starts at build launch · Started at 12:13 | **Started at 12:13**, so the hard stop is 15:13 |
| 2.2 | Repo | How are the repo and branches set up? | ★ Public, milestone PRs → `feat/dme-order-intake` → one release PR into `main` · Private + zip · Public with `develop` | **Public, main + PRs** |
| 2.3 | Frontend | How much frontend? | ★ Thin workflow UI · Review UI + PDF preview (~+45 min) · API + Swagger only | **Review UI + PDF preview** |
| 2.4 | PDF storage | What happens to the PDF after extraction? | ★ Discard it, keep values + evidence + hash · Store it | **Discard it** |

**Agent pushback (12:27, 14 minutes in):** two of these answers conflict.
1. *PDF preview vs. discarding the PDF.* A preview needs the file, but the server won't keep it. Proposed resolution: render the preview in the browser from the user's local copy (object URL) on the post-upload review screen only. The server never stores the PDF. Saved orders show evidence quotes and page numbers without the PDF.
2. *PDF preview vs. the timebox starting at 12:13.* About 2h45m is left for the build, two deploys and proof. The preview costs ~45 minutes. Proposed resolution: make it the last milestone, cut it if it hasn't started by 14:30, and ship the thin review UI no matter what.

## Round 2b (resolving the conflicts)

| # | Topic | Question | Options (★ = recommended) | Answer |
|---|-------|----------|---------------------------|--------|
| 2.5 | Preview | How does the preview work if the server discards PDFs? | ★ Browser-local preview only · Store PDFs after all | **Store PDFs.** "The question before was worded around archiving the PDF. Let's keep it for now so we can show it on the preview." (The human overrode 2.4: the agent's 2.4 wording framed storage as archiving.) |
| 2.6 | Scope cut | When does the preview get built? | ★ Last milestone, cut line 14:30 · Must ship | **Last milestone, cut line 14:30** |
| 2.7 | Eval | How is extraction quality proven? | ★ Synthetic eval set · Sample PDF only | **Both:** "DME Patient Demo Document CPAP.fax.pdf is our starting benchmark, but include the synthetic eval set on top to ensure full coverage" |
| 2.8 | Processing | Sync or async extraction? | ★ Synchronous · Async job + polling | **Synchronous for the assessment.** Document the async job + polling design as the scaling path |

**Agent findings from the benchmark PDF (3 pages + 1 blank, fax header):**
- Expected values: patient Marie Curie, DOB 12/05/1900, ordering provider (prescriber who signs the order) Arjun Raj D.P.M, NPI 9182734556.
- **The NPI fails the NPI Luhn checksum** (prefix 80840, computed check digit 5, actual 6). The correct behavior is to extract it but flag it, leaving the order in `needs_review`, not `ready`. This trap is probably deliberate.
- **Provider ambiguity:** page 2 lists a different "Referring Physician: Gregory House MD". The ordering provider is the prescriber on the order, not the referring physician.
- DOB 1900 means age 124 at the 2024 visit, an edge for plausibility rules. A strict "age ≤ 120" rule would wrongly reject it.
- Distractors: fax header dates, an impossible signature date "2/30/24", a blank page 4, and two different visit dates (02/24/24 vs 02/12/24).

## Round 3

| # | Topic | Question | Options (★ = recommended) | Answer |
|---|-------|----------|---------------------------|--------|
| 3.1 | PDF store | Where do stored PDFs live? | ★ Postgres bytea · Railway volume · S3/R2 | **Postgres bytea** |
| 3.2 | Bad values | Present but invalid value: what's stored? | ★ Keep it as read, flagged with an error issue · Null it | **Keep it, flagged** |
| 3.3 | NPPES | Verify NPIs against the CMS NPPES registry? | ★ Checksum + NPPES · Checksum only | **Backlog.** "Good idea, add it to the backlog and we'll do it if there's enough time left" |
| 3.4 | E2E proof | Which journeys must the headless browser prove? | Upload→review→fix→ready · User isolation · Manual CRUD · Missing-field upload | **Upload→review→fix→ready, user isolation, missing-field upload.** Manual CRUD is proven by API tests, not the browser |

## Plan review: change request 1 (human, ~13:00)

> "Commit throughout the development cycle after completed whole tasks rather than a single commit per milestone. Create separate in-depth documents covering data schemas, API endpoints and architecture. Generate a prototype UI using a Claude artifact to finalize the UI before milestone 4 starts."

**Agent response:**
1. Every milestone plan gets a numbered task list, and the builder commits after each completed task (conventional messages). The squash into `feat/dme-order-intake` is turned off: milestone PRs are merge commits, so the per-task history survives into `main`.
2. Three new docs in `docs/architecture/`: `data-schema.md`, `api.md`, `architecture.md`.
3. The UI prototype is built now as a Claude artifact, so it doesn't stop the autonomous chain mid-run. Once the human signs it off, it becomes M4's design source alongside `docs/context/designs/ui.md`.

## Plan review: change request 2 (human)

> "Let's try to use https://genhealth.ai/ — their own branding so the MVP looks part of their product line."

**Agent pushback:** Declined as asked. A publicly deployed sign-in page under GenHealth's name and logo, at a URL GenHealth doesn't own, looks like a real GenHealth login. That's an impersonation and phishing risk, and artifact policy also forbids imitating a real organization's branding. **Proposed instead:** "inspired-by" styling (a similar palette and type feel, no logo, no GenHealth product name, no copied assets), a neutral product name ("DME Intake"), and a footer saying "Take-home project for GenHealth.ai by Ernesto Rodriguez, not an official GenHealth product." _Awaiting the human's answer._

**Human's answer:** (a). Restyle with GenHealth-inspired colors and type, no logo or name, plus the disclaimer footer.
