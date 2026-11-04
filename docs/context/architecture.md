# Architecture

| Piece | Choice |
| --- | --- |
| Repo | Monorepo: `apps/web` (Next.js 15, TS, pnpm), `services/api` (FastAPI, Python 3.12, uv), root `Makefile` |
| API | FastAPI + Pydantic v2, SQLAlchemy 2 + Alembic, uvicorn |
| DB | Postgres 16. Local via docker compose, prod via the Railway plugin. Tables `users`, `orders`, `documents` |
| PDF storage | `documents.content` bytea, served only via an authenticated `GET /orders/{id}/document` |
| Extraction | `Extractor` protocol → `AnthropicExtractor` (`claude-opus-5-5`, native PDF, JSON-schema output, evidence per field) |
| Validation | `app/validation`: names, DOB, NPI (Luhn with prefix 80840), grounding. Runs on extract, create and patch |
| Auth | argon2id + HS256 JWT (60 min), bearer header, all queries owner-scoped |
| Web | Next.js App Router, Tailwind + shadcn/ui, calls the API directly. Types generated from OpenAPI |
| Hosting | Web on Vercel. API + Postgres on Railway (Docker). Secrets only in platform variables |
| Tests | API: pytest (+ testcontainers or compose Postgres). Web: Playwright e2e. `evals/` scores extraction on live Claude |
| Processing | Synchronous extraction (≤120s). Async worker is the documented scaling path |
