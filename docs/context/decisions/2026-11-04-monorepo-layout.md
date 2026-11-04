# ADR: Monorepo with a Next.js web app and a FastAPI service

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (decision log D1)

## Context
The brief requires a Python REST API (R6), and any frontend must be JS/TS. The human asked for one repo with a frontend and a service layer.

## Options
1. **Monorepo: `apps/web` (Next.js 15, TS) + `services/api` (FastAPI, Python 3.12, uv)**. One history, one PR per change, and shared docs. The two toolchains live side by side.
2. **Two repos.** Clean isolation, but graders would follow two histories, and cross-cutting changes in the pair session would need two PRs.
3. **Turborepo/Nx workspace.** Built for JS-only monorepos. Little value with a Python service.

## Decision
Option 1. A root `Makefile` is the one entry point: `make verify`, `make dev`, `make test`. `docker-compose.yml` runs Postgres locally.

## Consequences
- The frontend gets the API's types from FastAPI's OpenAPI schema (`openapi-typescript`), so there's no hand-written duplication.
- No monorepo build tool. Each app keeps its native tooling (pnpm, uv).
