# Backlog

Ranked. Pick up only once the MVP is live (decision log D17).

| # | Item | Why | Est. |
|---|------|-----|------|
| B1 | NPPES NPI Registry check: NPI exists, and the registry name matches the extracted provider name | Catches valid-checksum, wrong-provider errors | 15 min |
| B2 | Async extraction: job table + `SKIP LOCKED` worker, 202 + polling | Long faxes and concurrency (see `decisions/2026-11-04-sync-extraction.md`) | 45 min |
| B3 | Move PDFs to S3/R2 with signed URLs | DB size at scale | 30 min |
| B4 | Audit log of PHI reads and writes | HIPAA | 30 min |
| B5 | Password reset, email verification, refresh tokens | Real accounts | 1 h |
| B6 | Extract more order fields (HCPCS items, diagnosis codes, order date) | Fuller intake | 30 min |
| B7 | Move extraction to Bedrock under an AWS BAA, plus BAA-covered hosting | Production PHI (see `decisions/2026-11-04-hipaa-posture.md`) | 1 day |
| B8 | Persistent rate limiting (Redis) | The in-memory limiter resets per replica | 20 min |
| B9 | PDF preview pane (former M5), web-only on top of `GET /orders/{id}/document` | Cut at the 13:50 re-plan for time | 30 min |
