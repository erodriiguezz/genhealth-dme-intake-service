# ADR: Synchronous extraction in the upload request; async documented for scale

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D14)

## Context
Opus extraction takes 10–60s on a multi-page fax. Graders will curl the upload endpoint and expect a result.

## Options
1. **Synchronous:** `POST /orders/extract` (multipart) returns `201` with the saved order once extraction finishes. 120s server timeout. The UI shows a progress state.
2. **Async:** return `202` with an order in `processing`, a worker extracts, and the client polls `GET /orders/{id}` or gets a webhook. Robust at scale, retries, no long-held connections. Needs a queue (Redis/SQS or a Postgres `SKIP LOCKED` job table) plus a worker process, ~30+ minutes.

## Decision
Option 1 for the assessment.

**Scaling path (not built):** add `status=processing|failed` and a `jobs` table claimed with `SELECT … FOR UPDATE SKIP LOCKED` by a separate Railway worker service running the same image. `POST /orders/extract` returns 202, and the UI polls. Retries with backoff, and a dead-letter state after 3 tries. The `Extractor` interface is unchanged.

## Consequences
- A dropped connection loses the result (the order isn't saved if extraction fails). Concurrency is bounded by uvicorn workers.
