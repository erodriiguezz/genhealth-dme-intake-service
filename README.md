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

## How this was built

Built AI-natively in a 3-hour timebox. A lead agent (Claude Opus) asked the questions, planned and reviewed every PR. Parallel builder agents (Claude Sonnet) wrote the code, one commit per task. The whole trail is in the repo:

- [docs/process/](docs/process/): every planning question with its options and answers, the decision log, the timeline, and the agent's pushback (HIPAA, branding, scope cuts)
- [.claude/plans/](.claude/plans/): the approved MVP plan and the per-milestone plans with acceptance criteria
- The PRs: each one has a review comment, and its fixes are on the branch

**Cut for time** ([backlog](docs/backlog.md)): PDF preview pane, NPPES registry check, async extraction, S3 storage, password reset.
