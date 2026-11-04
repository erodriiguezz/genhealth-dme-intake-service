# Status

| Area | State |
| --- | --- |
| Plan | MVP `mvp-order-intake` approved and delivered 2026-11-04. M5 (PDF preview) cut to backlog B9 |
| Code | M1 scaffold, M2 auth/CRUD/validators/seed, M3a extraction core + evals, M3b upload/document endpoints, M4 web UI, M6 deployed journeys |
| Deploy | Live: web https://genhealth-dme-intake.vercel.app, API https://api-production-b3c6.up.railway.app. Migrations + seed run at container start |
| Quality | Live eval: 45/45 fields (100%), 0 no-guess violations, $0.23 for 9 docs. 122 API tests, Playwright suites, per-run test DB |
| Backlog | B1 NPPES, B2 async worker, B3 S3, B4 audit log, B5 password reset, B8 Redis limiter, B9 PDF preview |
