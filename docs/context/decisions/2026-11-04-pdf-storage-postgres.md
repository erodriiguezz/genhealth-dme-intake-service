# ADR: Store uploaded PDFs in Postgres (bytea)

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D11, D15)

## Context
The review UI shows the source PDF next to the extracted fields, so the PDF has to be kept. Volume is take-home scale.

## Options
1. **Postgres `bytea` in a `documents` table.** One datastore, transactional with the order, owner-scoped by the same query rules, and no extra credentials. Bloats the DB at scale.
2. **Railway volume.** Pins the API to one replica, and its backups are separate from the DB.
3. **S3/R2 with signed URLs.** The right answer at scale. Another vendor plus ~20 minutes of setup.

## Decision
Option 1. `documents(id, owner_id, filename, sha256, size_bytes, page_count, content bytea, created_at)`. List endpoints never select `content`. The PDF is served only through `GET /orders/{id}/document`, authenticated and owner-scoped, with `Content-Disposition: inline` and `Cache-Control: private, no-store`. Max 20 MB per upload.

## Consequences
- More PHI at rest than discarding would leave (accepted by the human). Deleting an order deletes its document.
- Migrating to S3 later means changing the storage adapter and writing a backfill script.
