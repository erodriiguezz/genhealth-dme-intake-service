# API reference (design)

FastAPI service at `services/api`. Live OpenAPI lives at `/docs` (Swagger) and `/openapi.json`. This doc is the contract the milestones implement. If the two disagree, the code's OpenAPI is the truth and this doc is fixed in the same PR.

- **Base URL:** local `http://localhost:8000`, prod `https://<railway-domain>` (recorded in the README after M1).
- **Format:** JSON (UTF-8). Dates are ISO `YYYY-MM-DD`, timestamps are RFC 3339 UTC, IDs are UUIDv4.
- **Auth:** `Authorization: Bearer <JWT>` on everything except `/health`, `/auth/register` and `/auth/login`.
- **CORS:** only the origins in `CORS_ORIGINS` (Vercel prod + localhost:3000). Credentials aren't used (bearer header).

## Errors

Every non-2xx response has the same shape:
```json
{ "error": { "code": "order_not_found", "message": "Order not found.", "details": null } }
```
FastAPI's 422 validation errors are reshaped to `code: "validation_error"`, with `details` set to a list of `{loc, msg}`.

| Status | When |
|---|---|
| 400 | Malformed request |
| 401 | Missing, invalid or expired token (`WWW-Authenticate: Bearer`) |
| 404 | Resource doesn't exist **or belongs to another user**. Never 403, so IDs can't be enumerated |
| 409 | Email already registered |
| 413 | Upload over 20 MB |
| 415 | Upload isn't a PDF |
| 422 | Body validation failed, or the PDF is encrypted, corrupt or over 100 pages |
| 429 | Rate limited (`Retry-After` set) |
| 502 | Extractor failed or timed out. Nothing was saved. Retryable |
| 503 | Extraction not configured (no `ANTHROPIC_API_KEY`) |

## Endpoints

### `GET /health`
No auth. `200 {"status":"ok","db":"ok"}`, or `503 {"status":"degraded","db":"error"}`. Never exposes versions or config.

### `POST /auth/register`
```json
{ "email": "mike@genhealth.ai", "password": "at-least-8-chars" }
```
`201 {"id": "…", "email": "mike@genhealth.ai", "created_at": "…"}` · `409 email_taken` · `422` (bad email, password under 8 or over 128 characters) · `429` (10/min per IP).

### `POST /auth/login`
`application/x-www-form-urlencoded` (OAuth2 password flow, so Swagger's **Authorize** button works): `username=<email>&password=<pw>`.
`200 {"access_token":"<jwt>","token_type":"bearer","expires_in":3600}` · `401 invalid_credentials` (same message for an unknown email and a wrong password) · `429`.

JWT claims: `sub` (user id), `iat`, `exp` (+60 min), signed HS256 with `JWT_SECRET`.

### `GET /auth/me`
`200 {"id","email","created_at"}` · `401`.

### `GET /orders`
Query: `status` (`needs_review` | `ready`, optional), `limit` (1–100, default 50), `offset` (default 0).
`200 {"items": [OrderSummary], "total": 3}`, newest first. **Only the caller's orders.**

`OrderSummary` = `Order` without `extraction` (keeps lists light). `document` gives metadata only, never content.

### `POST /orders` (manual create)
```json
{
  "patient_first_name": "Jane",
  "patient_last_name": "Doe",
  "patient_dob": "1961-03-14",
  "provider_name": "Ann Lee MD",
  "provider_npi": "1234567893"
}
```
All fields are optional (missing ones become `not_found` issues). `status`, `issues`, `owner_id` and `extraction` are **not accepted**; extra keys give 422. A `patient_dob` that isn't an ISO date gives 422 (manual entry is typed; only extraction parses free text).
`201 Order`.

### `GET /orders/{id}`
`200 Order` · `404 order_not_found`.

### `PATCH /orders/{id}`
Partial update with the same fields as create. Sending `null` clears a field (it then becomes `not_found`). The server merges, re-runs every validator, drops `extraction`-source issues for the edited fields, and re-derives `status`.
`200 Order` · `404` · `422`.

### `DELETE /orders/{id}`
Deletes the order and its document in one transaction. `204` · `404`.

### `POST /orders/extract`
`multipart/form-data` with one part, `file` (the PDF). **Synchronous**: the response arrives once extraction and validation finish (typically 10–40 s, server timeout 120 s).

Pipeline:
1. Auth, then the per-user rate limit (20/hour).
2. Stream to memory with a hard 20 MB limit → 413.
3. Check the `%PDF-` magic → 415. Parse with `pypdf`: encrypted, corrupt or over 100 pages → 422.
4. `Extractor.extract(pdf_bytes)` → per-field `{value, evidence, page}`. Timeout or API error → 502, nothing saved.
5. Grounding: a value its evidence doesn't contain is dropped, with an `ungrounded` issue.
6. Parse the DOB (US `MM/DD/YYYY` → ISO → `Month D, YYYY`). Normalize the NPI to digits.
7. Validators → issues → status.
8. Insert the document and the order in one transaction → `201 Order`.

```bash
curl -sS -X POST "$API/orders/extract" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@DME Patient Demo Document CPAP.fax.pdf;type=application/pdf"
```

### `GET /orders/{id}/document`
`200` `application/pdf` with `Content-Disposition: inline; filename="<sanitized>"`, `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`. `404` if the order doesn't exist, isn't the caller's, or has no document.

## The `Order` object
```json
{
  "id": "6f1c…",
  "status": "needs_review",
  "patient_first_name": "Marie",
  "patient_last_name": "Curie",
  "patient_dob": "1900-12-05",
  "provider_name": "Arjun Raj D.P.M",
  "provider_npi": "9182734556",
  "issues": [
    { "field": "provider_npi", "code": "npi.checksum_failed", "severity": "error", "message": "Fails the NPI checksum. This isn't a valid NPI as written.", "source": "validation" },
    { "field": "patient_dob", "code": "dob.age_over_120", "severity": "warning", "message": "Patient would be 124 years old. Check the date.", "source": "validation" },
    { "field": "provider_name", "code": "provider.multiple_candidates", "severity": "warning", "message": "Also on the document: Gregory House MD (referring physician, p.2).", "source": "extraction" }
  ],
  "extraction": { "model": "claude-opus-5-5", "latency_ms": 18432, "fields": { "…": "see data-schema.md" }, "provider_candidates": [] },
  "document": { "id": "a0b2…", "filename": "DME Patient Demo Document CPAP.fax.pdf", "page_count": 4, "size_bytes": 1992294 },
  "created_at": "2026-11-04T18:02:11Z",
  "updated_at": "2026-11-04T18:02:11Z"
}
```

## Walkthrough (also in the README, run against deployed in M6)
```bash
API=https://<railway-domain>
curl -sS -X POST $API/auth/register -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"correct-horse-9"}'
TOKEN=$(curl -sS -X POST $API/auth/login -d 'username=you@example.com&password=correct-horse-9' | jq -r .access_token)
ORDER=$(curl -sS -X POST $API/orders/extract -H "Authorization: Bearer $TOKEN" -F "file=@sample.pdf" | tee /dev/stderr | jq -r .id)
curl -sS -X PATCH $API/orders/$ORDER -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"provider_npi":"1234567893"}' | jq '{status, issues}'
curl -sS -X DELETE $API/orders/$ORDER -H "Authorization: Bearer $TOKEN" -o /dev/null -w '%{http_code}\n'
```

## Rate limits (in-memory, per API replica)
| Route | Limit | Key |
|---|---|---|
| `/auth/register`, `/auth/login` | 10 / min | client IP |
| `/orders/extract` | 20 / hour | user id |

They reset on deploy. A Redis-backed limiter is backlog B8.
