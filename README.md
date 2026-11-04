# GenHealth DME Intake

Upload a physician order, extract the fields, review and edit them. FastAPI + Postgres (API), Next.js (web).

## Live

- Web: _pending deploy_
- API: _pending deploy_ (`/health`)

## Run locally

Needs Docker, uv, Node 20+ and pnpm.

```bash
# copy services/api/.env.example and apps/web/.env.example to local env files and fill them in
docker compose up -d --wait && make migrate
cd services/api && uv sync && cd ../../apps/web && pnpm install && cd ../..
make dev        # API :8000, web :3000
make verify     # ruff, pytest (intake_test DB), tsc, eslint
```

If host port 5433 is taken, run everything with `DB_PORT=<free port>` and set `DATABASE_URL` to match.

Browser smoke tests: `cd e2e && pnpm install && npx playwright install chromium && npx playwright test` (`BASE_URL` defaults to `http://localhost:3000`).
