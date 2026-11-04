# ADR: Host the web app on Vercel and the API + Postgres on Railway

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D3, D9)

## Context
R5: the service must be publicly reachable with a working upload endpoint (hard gate). Multi-page scanned PDFs can exceed 4.5 MB.

## Options
1. **Python API on Vercel serverless.** Rejected: the 4.5 MB request-body limit breaks uploads, and long extractions hit function timeouts.
2. **Vercel + Render + Neon** (the agent's recommendation). Cheap, but it's three vendors, and the free tier has cold starts.
3. **Vercel + Railway** (the human's choice). The API runs as a Docker service and Postgres as a Railway plugin in one project. No cold starts on the Hobby plan, and the request duration covers 60s extractions.

## Decision
Option 3. `services/api/Dockerfile` + `railway.json`, with Alembic migrations as the pre-deploy command. Next.js runs on Vercel Hobby, with `NEXT_PUBLIC_API_URL` pointing at the Railway domain. CORS allows only the Vercel production domain and localhost. Deploys go through the CLI (`railway up`, `vercel deploy --prod`) during the build. GitHub auto-deploy from `main` is switched on after the feature-release PR merges.

## Consequences
- Railway is paid after the trial ($5/mo Hobby). Secrets (`ANTHROPIC_API_KEY`, `JWT_SECRET`, `DATABASE_URL`) live only in Railway variables, entered by the human.
- Neither free tier signs a BAA (see the HIPAA ADR).
