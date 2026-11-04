# DME Intake: order-intake service

A take-home for GenHealth.ai: turn a faxed DME order PDF into a validated order record, without ever guessing a value.

Upload a PDF. Claude reads it (scans and handwriting included) and returns the patient's first name, last name and date of birth, plus the ordering provider's name and NPI. Each value comes with the verbatim quote and page it was read from. Deterministic checks then run before anything is saved: grounding, DOB rules, NPI format/prefix/Luhn. A missing or invalid field is flagged and the order stays **Needs review** until a person fixes it. Each user sees only their own orders.

> Not an official GenHealth product. Demo data only, so please don't upload real patient data.

## Live

| | URL |
|---|---|
| Web app | https://genhealth-dme-intake.vercel.app |
| API | https://api-production-b3c6.up.railway.app |
| API docs (Swagger, has an **Authorize** button) | https://api-production-b3c6.up.railway.app/docs |
| Health | https://api-production-b3c6.up.railway.app/health |

**Reviewer accounts:** `mahum@genhealth.ai` and `mike@genhealth.ai` are pre-created. Passwords were sent with the submission email; they're never in the repo. You can also just sign up with any email.

## Try it in 60 seconds (curl)

```bash
API=https://api-production-b3c6.up.railway.app
curl -sS -X POST $API/auth/register -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"correct-horse-9"}'
TOKEN=$(curl -sS -X POST $API/auth/login \
  --data-urlencode username=you@example.com --data-urlencode password=correct-horse-9 | jq -r .access_token)

# Upload a PDF. Synchronous, typically 10–40 s for a multi-page fax.
ORDER=$(curl -sS -X POST $API/orders/extract -H "Authorization: Bearer $TOKEN" \
  -F "file=@evals/cases/genhealth-cpap-fax.pdf;type=application/pdf" | tee /dev/stderr | jq -r .id)

# The sample fax's NPI fails the checksum, so the order is needs_review. Fix it:
curl -sS -X PATCH $API/orders/$ORDER -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"provider_npi":"1234567893"}' | jq '{status, issues}'

curl -sS $API/orders -H "Authorization: Bearer $TOKEN" | jq '.items[] | {id, status}'
curl -sS -X DELETE $API/orders/$ORDER -H "Authorization: Bearer $TOKEN" -o /dev/null -w '%{http_code}\n'
```

| Endpoint | What it does |
|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Email + password (argon2id). Login returns a 60-min JWT bearer token |
| `GET /orders`, `POST /orders` | List (`?status=needs_review\|ready`) and manual create |
| `GET/PATCH/DELETE /orders/{id}` | Read, edit (re-validates), delete. Another user's order → **404** |
| `POST /orders/extract` | Upload a PDF (≤20 MB, ≤100 pages) → extracted, validated, saved order |
| `GET /orders/{id}/document` | The original PDF, owner only |

Full contract: [docs/architecture/api.md](docs/architecture/api.md).

## How "don't guess" is enforced

| Guard | What it stops |
|---|---|
| Prompt: return null unless the value is explicitly present, and copy it exactly | Filling in a DOB from an "AGE: 124" line, or "fixing" digits |
| Prompt: the ordering provider is the prescriber, and all other providers are listed | Picking the referring physician (the sample fax names one on p.2) |
| Prompt: the document is untrusted data | Prompt injection inside a fax (there's a case for it in the eval set) |
| **Grounding:** each value must appear in its own quoted evidence, on digit and word boundaries | Hallucinated or partial values. These are dropped and flagged `…ungrounded` |
| Validators: names, DOB (future/impossible = error, age >120 = warning), NPI (10 digits, starts 1/2, Luhn over `80840`) | Typos and misreads. **Invalid values are kept exactly as read and flagged, never "corrected"** |
| Status is derived server-side, plus a DB `CHECK` | An order can't be `ready` with a missing field or an error issue |

## Extraction quality (live, Claude Opus 5.5)

`make eval` runs the extractor on the GenHealth sample fax plus 8 synthetic documents. All are fake data: a clean order, a rotated noisy scan, fields on page 3 of 4, a missing DOB, an invalid NPI, a referring-physician distractor, handwritten-style text, and a prompt injection.

**Latest run:** 45/45 fields correct (100%) · **0 no-guess violations** · ~$0.23 for all 9 · [details](docs/evidence/extraction-eval.md)

## Architecture

```
Browser ──► Next.js 16 (Vercel) ──┐
   └──────── bearer JWT ──────────┴──► FastAPI (Railway, Docker) ──► Postgres 16 (Railway)
                                              └──► Claude API (claude-opus-5-5, native PDF input)
```

- `services/api`: FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2, uv. Layers: routers → services (owner scoping, transactions) → pure validation/grounding → adapters (the `Extractor` protocol, so Bedrock is a config swap)
- `apps/web`: Next.js 16, Tailwind, shadcn/ui
- `evals/`: extraction eval set + runner. `e2e/`: Playwright
- Docs: [architecture](docs/architecture/architecture.md) · [data schema](docs/architecture/schema.md) ([DDL](docs/architecture/schema.sql)) · [API](docs/architecture/api.md) · [ADRs](docs/context/decisions/) · [UI design + prototype](docs/context/designs/)

**HIPAA note:** real PHI would need BAAs with every vendor (LLM, hosting, DB). The code is built for that path: no PHI in logs, owner-only access, `no-store` PDFs, and a swappable LLM provider. The free hosting used here isn't BAA-covered. See the [HIPAA ADR](docs/context/decisions/2026-11-04-hipaa-posture.md).

## Run locally

Needs Docker, uv, Node 20+ and pnpm.

```bash
cp services/api/.env.example services/api/.env   # add ANTHROPIC_API_KEY
cp apps/web/.env.example apps/web/.env.local
docker compose up -d --wait && make migrate
(cd services/api && uv sync) && (cd apps/web && pnpm install)
make dev        # API :8000, web :3000
make verify     # ruff + pytest (each run uses its own throwaway DB) + tsc + eslint
make eval       # live extraction eval (~$0.25)
```

The local Postgres runs on host port **55433**. Override with `DB_PORT=<port>`.

## Hand-off: picking this project up

For a new developer taking over. Read this section, then `docs/architecture/architecture.md`.

### Day one checklist
1. **Access:** GitHub repo (admin), the Railway project `genhealth-dme-intake` (services `api` + `Postgres`), the Vercel project `genhealth-dme-intake`, and an Anthropic API key of your own.
2. **Run it locally** (see [Run locally](#run-locally)), then `make verify` (should report ~122 passed) and `make eval` (should report 100% / 0 no-guess violations).
3. **Walk the product** with [docs/reviews/mvp-order-intake.md](docs/reviews/mvp-order-intake.md), using the test PDFs in `evals/cases/` (expected outcomes in `evals/cases/expected.json`).
4. **Skim the decisions:** [docs/process/decision-log.md](docs/process/decision-log.md) (D1–D32, one line each, who decided and why) and the ADRs in `docs/context/decisions/`.

### Where things live
| Area | Path | Notes |
|---|---|---|
| HTTP routes | `services/api/app/routers/` | Thin: parse, call a service, serialize. No SQL here |
| Use cases + owner scoping | `services/api/app/services/` | **Every query filters by `owner_id`.** Keep it that way: other users' rows must look like 404s |
| Validation rules | `services/api/app/validation/` | Pure functions → `Issue` lists. The easiest place to add a rule |
| Extraction | `services/api/app/extraction/` | `Extractor` protocol, Anthropic + fake implementations, prompt, JSON schema, grounding |
| Upload size cap | `services/api/app/upload_limit.py` | ASGI middleware. It runs *before* multipart parsing |
| DB schema | `docs/architecture/schema.sql` → `services/api/alembic/versions/` | The reviewed DDL is the source of truth. `make schema-diff` proves the migrations match it |
| Web app | `apps/web/app/`, `apps/web/components/`, `apps/web/lib/api.ts` | Next.js **16**. Read `apps/web/AGENTS.md` first, because its APIs differ from older Next |
| Tests | `services/api/tests/` (pytest), `e2e/` (Playwright), `evals/` (live model) | |
| Planning context | `docs/context/` (product, architecture, domain, status tables), `.claude/plans/` | Short tables. Update the row your change makes wrong |

### Common changes
- **Add an extracted field** (e.g. HCPCS code):
  1. Add it to `extraction/schema.py`, `prompt.py` and `base.py`.
  2. Add a column in a new Alembic migration, and mirror it in `schema.sql`.
  3. Add a validator, and update `schemas.py` + `apps/web/lib/api-types.ts`.
  4. Add the expected value to the eval cases, then run `make eval`.
- **Change the prompt:** bump `PROMPT_VERSION` in `extraction/prompt.py`, then run `make eval` and commit `docs/evidence/extraction-eval.*`. Every saved order records the prompt version it was extracted with.
- **Add a validation rule:** a pure function in `validation/` returning an `Issue`, plus a unit test. `error` blocks `ready`; `warning` doesn't. Status is derived for you. Never set it by hand.
- **Switch the model or provider:** set the `EXTRACTION_MODEL` env var. A new provider (e.g. AWS Bedrock for HIPAA) is a new `Extractor` implementation registered in `extraction/factory.py`.

### Deploys and environments
| | Web | API + DB |
|---|---|---|
| Host | Vercel, project root **`apps/web`** | Railway: service `api` (Docker, `services/api/Dockerfile`) + `Postgres` |
| Deploy | Git integration on `main` (needs Root Directory = `apps/web`), or `cd apps/web && vercel deploy --prod` | `cd services/api && railway up --service api` (CLI). There's no Git auto-deploy yet |
| On start | — | `alembic upgrade head && python -m app.seed && uvicorn …`. Migrations run at container start, which assumes **one replica** (`numReplicas: 1`) |
| Health | `/login` | `/health` (checks the DB) |

**Environment variables** (secrets live only in the platform dashboards, never in the repo. Templates: `services/api/.env.example`, `apps/web/.env.example`):

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | Railway api (a reference to Postgres) | DB connection |
| `ANTHROPIC_API_KEY` | Railway api | Extraction. Without it, upload returns 503 |
| `JWT_SECRET` | Railway api | Token signing, ≥32 chars in production. Rotating it logs everyone out |
| `SEED_USERS` | Railway api | `email:pw,email:pw`. Creates missing accounts at start and never changes existing passwords |
| `ENV` | Railway api | `production` refuses the fake extractor and weak secrets |
| `EXTRACTION_MODEL` / `EXTRACTION_PROVIDER` | Railway api | `claude-opus-5-5` / `anthropic` |
| `CORS_ORIGINS` | Railway api | The Vercel URL |
| `NEXT_PUBLIC_API_URL` | Vercel | The API base URL |

Railway applies dashboard variable edits only after you click **Deploy / Apply changes**.

### Gotchas we already hit
- **Structured-output schema limit:** the Claude API rejects JSON schemas with more than 16 nullable/union fields (we had 19, and every call returned 400). Mocked tests can't catch this, so run `make eval` after any schema change.
- **Pre-deploy hooks:** Railway didn't run `preDeployCommand` for CLI deploys, and production had no tables. That's why migrations moved into the container start command.
- **Local DB port:** the default is 55433 because 5432–5436 are often taken. Each pytest run creates and drops its own throwaway database, so parallel runs are safe.
- **Fresh checkout typecheck:** Next 16 generates `LayoutProps`, and `make verify` runs `next typegen` before `tsc`.
- **PHI in logs:** never log field values, filenames or `str(exc)` of DB errors (Postgres puts the row in the error text). The engine uses `hide_parameters=True`, and IntegrityErrors log only the constraint name.
- **Rate limits are in memory** (register/login 10/min/IP, extract 20/hour/user) and reset on deploy. Back-to-back e2e runs against production can hit 429.
- **Synchronous extraction:** an upload holds the request for 10–40 s (110 s timeout). Fine at this scale, but see the async design in `docs/context/decisions/2026-11-04-sync-extraction.md`.

### Known gaps (ranked) and what's next
Full list: [docs/backlog.md](docs/backlog.md).
1. **HIPAA readiness** before any real PHI: BAAs (Anthropic or Bedrock, plus BAA-covered hosting), an audit log, retention policy. See the HIPAA ADR.
2. **NPPES lookup:** check that the NPI exists and matches the provider name (B1, ~15 min).
3. **Async extraction worker** for long faxes and concurrency (B2).
4. **PDF preview pane** on the review screen, which is web-only on top of `GET /orders/{id}/document` (B9).
5. **Small items:** password reset and refresh tokens, a Redis rate limiter, S3 for PDFs, a CSP nonce instead of `unsafe-inline`, and a "session expired" message. A PATCH can show both `ungrounded` and `not_found` for one field (cosmetic).
6. **CI:** there are no GitHub Actions yet. `make verify` + `make schema-diff` + the stubbed Playwright suite are the gate to wire up.

### Ways of working
- **Branches:** `<type>/<short-description>` (`feat`, `bugfix`, `hotfix`, `chore`, `refactor`). **Commits:** `type: description`, lowercase imperative, one per completed task. PR titles mirror commits.
- **`main` is production.** Merge only by PR, after `make verify` passes and the PR has a review.
- **Big changes start with a plan** in `.claude/plans/`: what, why, how, blast radius, acceptance criteria. Record real choices as ADRs in `docs/context/decisions/`.

## How this was built

Built AI-natively in a 3-hour timebox. A lead agent (Claude Opus) asked the questions, planned and reviewed every PR. Parallel builder agents (Claude Sonnet) wrote the code, one commit per task. The whole trail is in the repo:

- [docs/process/](docs/process/): every planning question with its options and answers, the decision log, the timeline, and the agent's pushback (HIPAA, branding, scope cuts)
- [.claude/plans/](.claude/plans/): the approved MVP plan and the per-milestone plans with acceptance criteria
- The PRs: each one has a review comment, and its fixes are on the branch

**Cut for time** ([backlog](docs/backlog.md)): PDF preview pane, NPPES registry check, async extraction, S3 storage, password reset.
