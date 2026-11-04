---
issue: M1
title: Scaffold monorepo, health check and deploy skeleton
branch: feat/dme-order-intake-p1-scaffold
status: approved
approved_by: Ernesto
approved_at: 2026-11-04
autonomy: pr
source: mvp
mvp: mvp-order-intake
size: M
est_tokens: 330000
est_lines: 500
shape: single
feature_branch: feat/dme-order-intake
base: feat/dme-order-intake
touches_api: true
tier: high
queue: false
shaped: 2026-11-04
---

# #M1 Scaffold monorepo, health check and deploy skeleton

## 1. Approval summary
**What:** The repo is bootstrapped (`main` and `feat/dme-order-intake` on GitHub, with no secret committed). The FastAPI service and the Next.js app boot locally against compose Postgres, `make verify` is green, and both are **already live**: API + private Postgres on Railway, web on Vercel. The web home page checks the API from the browser and shows ok / degraded / unreachable.

**Why:** R5 (public URL) is a hard gate, so deploy risk is retired first. A deploy that fails twice is a Hand-off that pauses the MVP chain, about 13:15 instead of 14:55. Every later milestone tests against the running app through `.claude/project.json`.

**How:** uv-managed FastAPI with `GET /health` (`SELECT 1`, 2 s timeout, 503 when the DB is down). `create-next-app` + shadcn init, with a client-side status fetch so the deployed check proves CORS and the baked-in API URL. Deployed by CLI (`railway up`, `vercel deploy --prod`). Turned down: GitHub auto-deploy now (switched on after the release PR), and a server-side status fetch (it proves nothing about CORS).

**Blast radius**
- Touches: new git repo + GitHub remote `erodriiguezz/genhealth-dme-intake-service`; new Railway project `genhealth-dme-intake` (personal workspace, Postgres + API service); new Vercel project `genhealth-dme-intake` (erodriiguezz)
- Files to touch:
  - `.gitignore`: written **before anything is staged**. Node, Python, `.env` and `.env.*` at any depth except `*.example`, `.vercel/`, plus the lines from `~/.claude/skills/plan/templates/gitignore`
  - `Makefile`: `verify` (starts compose `db` first), `dev`, `test`, `migrate`, `seed`, `eval`, `fmt`
  - `docker-compose.yml`: Postgres 16 on host port **5433**, with a healthcheck
  - `docker/initdb/01-test-db.sql`: creates the `intake_test` database
  - `services/api/pyproject.toml`, `services/api/uv.lock`: Python 3.12 (uv-managed); fastapi, uvicorn, sqlalchemy, alembic, psycopg, pydantic-settings, pytest, httpx, ruff
  - `services/api/app/main.py`: app factory, CORSMiddleware from `CORS_ORIGINS` (exact list)
  - `services/api/app/config.py`: pydantic-settings, `env_file=services/api/.env`, `postgresql://` → `postgresql+psycopg://`
  - `services/api/app/db.py`: engine and session dependency
  - `services/api/app/routers/health.py`: `{status, db}`, 200 or 503
  - `services/api/alembic.ini`, `services/api/alembic/env.py`: empty baseline
  - `services/api/Dockerfile`: uv install, `uvicorn … --port $PORT --timeout-keep-alive 130`
  - `services/api/railway.json`: `healthcheckPath: /health`, `preDeployCommand: alembic upgrade head`
  - `services/api/.env.example`: `DATABASE_URL` (port 5433), `TEST_DATABASE_URL`, `ANTHROPIC_API_KEY`, `EXTRACTION_MODEL`, `JWT_SECRET`, `CORS_ORIGINS`, `SEED_USERS`
  - `services/api/tests/conftest.py`, `services/api/tests/test_health.py`
  - `apps/web/**`: Next scaffold, shadcn init, demo PHI banner
  - `apps/web/components/api-status.tsx`: client component with the loading / ok / degraded / unreachable states
  - `apps/web/.env.example`: `NEXT_PUBLIC_API_URL`
  - `e2e/package.json`, `e2e/playwright.config.ts` (`BASE_URL`), `e2e/smoke.spec.ts`
  - `.claude/project.json`: verify, app recipe, webUrl/apiUrl, production URLs
  - `.claude/qa/api-smoke.json`: `/health` checks
  - `README.md`: stub, how to run, live URLs
  - `docs/evidence/M1.json`: proof and screenshots
- Also affected: `docs/` and `.claude/plans/` go into the first commit on `main` unchanged
- Left alone: the contents of `docs/` (written by the lead), `services/api/.env` (yours; agents never open it)
- Rollback: delete the Railway and Vercel projects, then force-reset the remote branches by hand (yours to do; agents never force-push)

**Concerns:**
- Railway is on Trial or unknown. If project or Postgres creation fails, that's a Hand-off (the deploy gate), with no workaround.
- Timebox: M1 can't be cut. If it isn't merged by 13:35, the chain goes on and the existing cut order (M5, then eval size, then polish) absorbs it. Accepted.
- If the Vercel name is taken, M1 uses the alias Vercel assigns and records it. CORS uses that exact origin.
- Python 3.12 isn't on PATH. uv installs it (`uv python install 3.12`).
- The root `.env` may still exist. It's ignored by the same rule and is never staged.

**Security:**
- Data in and out: none yet. `/health` returns `{status, db}` only, with no versions, hosts or errors
- Who can access it: public `/health`. CORS allows only the Vercel prod alias and `http://localhost:3000`
- Stored: none. `JWT_SECRET` is generated inside the `railway variables` command and never printed. Postgres is private-network only, with no public TCP proxy
- Abuse: secret leak into the public repo. Control: `.gitignore` first, explicit-path staging only (never `git add -A` or `.`), and before **every** push `git ls-files | grep -E '(^|/)\.env($|\.)' | grep -v '\.example$'` must be empty and `git check-ignore .env services/api/.env` must match. Any failure stops the push

**Acceptance criteria**
- **Repo bootstrap** (AC-M1.0): `.gitignore` is committed first. `main` (docs, plans, .gitignore) and `feat/dme-order-intake` exist on the GitHub remote. `git ls-files` contains no `.env` other than `*.example`, and the leak check passes before each push.
- **Local boot** (AC-M1.1): after `docker compose up -d --wait && make migrate && make dev`, `GET localhost:8000/health` returns `200 {"status":"ok","db":"ok"}`.
- **DB down** (AC-M1.5): with the DB unreachable or the check timing out after 2 s, `/health` returns `503 {"status":"degraded","db":"down"}`.
- **Web states** (AC-M1.6): `localhost:3000` shows a loading state, then "API: ok". With `/health` mocked to 503 it shows "API: degraded (db down)", and with the network aborted it shows "API: unreachable".
- **Verify** (AC-M1.2): `make verify` exits 0 (starts compose db; ruff, format check, pytest on `intake_test`, tsc, eslint).
- **Smoke** (AC-M1.3): `e2e/smoke.spec.ts` passes headless against local, covering all of AC-M1.6.
- **Deployed** (AC-M1.4): curl of the Railway URL `/health` returns 200 with `db: ok`. `smoke.spec.ts` with `BASE_URL=<vercel prod>` shows "API: ok" with no CORS console errors. Both URLs are in `.claude/project.json` and the README, and screenshots are in `docs/evidence/M1.json`.

**How it will be proven:** pytest (ok, 503, timeout) · API smoke against local and Railway · Playwright against local (all states) and the Vercel prod URL (ok)

**Size** M · ~500 lines · ~330k tokens · single PR

**Out of scope:** auth, models and migrations beyond the empty baseline, shadcn components, CI workflows, Git-connected auto-deploy, Vercel preview origins in CORS, public DB proxy

**Context:** `status.md`, "Deploy" row: the live URLs

---
## 2. Grill
Shape mode, 2026-11-04 12:51. Earlier rounds: `docs/process/grill-log.md` (rounds 1–3).

| # | Topic | Question | Answer |
| --- | --- | --- | --- |
| S1.1 | What | Who creates `main` and `feat/dme-order-intake` (the repo and remote are empty)? | M1 does it → AC-M1.0 |
| S1.2 | What | `/health` when the DB is down? | 503 `{"status":"degraded","db":"down"}` |
| S1.3 | What | Web status states? | loading / ok / degraded / unreachable |
| S2.1 | Why | Deploy fails after 2 tries? | Hand-off, the chain stops |
| S3.1 | How | CORS origins? | Vercel prod alias + localhost:3000 only |
| S3.2 | How | Status fetch side? | Client-side (proves CORS) |
| S4.1 | Blast radius | Accounts and names? | Personal, `genhealth-dme-intake` on both |
| S4.2 | Blast radius | Railway plan? | Trial / unsure → M1 checks; failure = Hand-off |
| S5.1 | Concerns | M1 not merged by 13:35? | Accept, existing cut order |
| S5.2 | Concerns | Anthropic key in place? | Was in the root `.env`; user moved it to `services/api/.env` |
| S6.1 | Security | Env location? | `services/api/.env` (user moved it) |
| S6.2 | Security | First-commit leak guard? | `.gitignore` first + explicit staging + pre-push check |
| S6.3 | Security | Postgres exposure? | Private network only |
| S7.1 | Proof | Test DB for verify? | Compose auto-started, `intake_test` DB |
| S7.2 | Proof | Deployed proof? | curl + Playwright on the Vercel prod URL |
| S8.1 | Edge cases | Vercel name taken? | Use the assigned alias, record it |
| S8.2 | Edge cases | Local DB port? | 5433 |
| S9 | Out of scope | — | Not asked; assumed unchanged (see Out of scope) |

Assumed without asking: a 2 s DB-check timeout, and the deploy order below.

## 3. Design & architecture
### Approach
- **Bootstrap order:** `git init -b main` → write `.gitignore` → `git add .gitignore docs .claude/plans` → leak check → commit `chore: bootstrap repo with plans and docs` → add the remote, push `main` → `git switch -c feat/dme-order-intake`, push → `git switch -c feat/dme-order-intake-p1-scaffold`.
- **Config:** pydantic-settings reads `services/api/.env` locally and platform variables on Railway. Railway's `postgresql://` URL is normalized to `postgresql+psycopg://`. Tests use `TEST_DATABASE_URL` (`intake_test` on 5433).
- **Health:** `SELECT 1` with `statement_timeout`/connect timeout of 2 s. Any exception → 503 `{"status":"degraded","db":"down"}`. The error is logged without details in the body.
- **Deploy order** (the API URL is baked into the web build, and the web origin goes into CORS): `railway init -n genhealth-dme-intake` → `railway add -d postgres` → API service from `services/api`, `DATABASE_URL` referenced from the Postgres service (private) → set `JWT_SECRET` (generated inline, not echoed) → `railway up` → `railway domain` → `vercel link` / project `genhealth-dme-intake`, root `apps/web`, set `NEXT_PUBLIC_API_URL` → `vercel deploy --prod` → read the prod alias → set `CORS_ORIGINS=<alias>,http://localhost:3000` on Railway → redeploy the API → curl + Playwright.
- **Web:** `api-status.tsx` is a `"use client"` component that fetches `${NEXT_PUBLIC_API_URL}/health` with a 5 s abort. 200 → ok, 503 → degraded, any throw → unreachable.

### Alternatives
| Choice | Picked | Rejected and why |
| --- | --- | --- |
| Status fetch | Client-side | Server component: hides CORS bugs until M4 |
| CORS | Exact origins | Preview regex: looser, and no preview deploys before the release |
| Test DB | Compose `intake_test` | testcontainers: slower, one more dependency |
| DB exposure | Private | Public proxy: internet-exposed DB for debugging convenience |

### Decisions
`docs/context/decisions/2026-11-04-monorepo-layout.md`, `2026-11-04-hosting-vercel-railway.md`. No new ADR: every choice here sits inside those two.

## 4. Plan
### Tests to add
- `services/api/tests/test_health.py`: ok with the DB up (AC-M1.1); 503 when the DB dependency raises (AC-M1.5); 503 on timeout (AC-M1.5)
- `.claude/qa/api-smoke.json`: GET `/health` returns 200 + `db: ok`, local and Railway (AC-M1.1, AC-M1.4)
- `e2e/smoke.spec.ts`: loading → "API: ok"; `page.route` 503 → "API: degraded (db down)"; `route.abort()` → "API: unreachable"; no console errors (AC-M1.3, AC-M1.6); the ok case with `BASE_URL` = Vercel prod (AC-M1.4)
- Bootstrap check (scripted in deliver, recorded in evidence): the leak check output before each push (AC-M1.0)

### Screens
- `/`: placeholder home with the API status (loading / ok / degraded / unreachable) and the demo PHI banner. Matches `docs/context/designs/ui.md` tokens. Light mode only; must not break at 390 px.

### Context
| File | Row | Change |
| --- | --- | --- |
| status.md | Deploy | Live: web <vercel url>, API <railway url> |

## 5. Evidence
## 6. Retro
## 7. Hand-off
