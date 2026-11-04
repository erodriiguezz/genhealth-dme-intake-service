---
issue: M2
title: Users, auth, seeded reviewers and owner-scoped Order CRUD with validation
branch: feat/dme-order-intake-p2-data-auth
status: draft
approved_by:
approved_at:
autonomy: pr
source: mvp
mvp: mvp-order-intake
size: L
est_tokens: 450000
est_lines: 650
shape: single
feature_branch: feat/dme-order-intake
base: feat/dme-order-intake
touches_api: true
tier: high
queue: false
---

# #M2 Users, auth, seeded reviewers and owner-scoped Order CRUD with validation

## 1. Approval summary
**What:** Register/login with JWT, reviewer accounts seeded from env, and full Order CRUD persisted in Postgres and scoped to the caller. Every create and patch runs the shared validators and derives the issues and status.

**Why:** R1, R3 and R4. The validators are shared with extraction (M3), so they're built and tested once, here.

**How:** SQLAlchemy models + an Alembic migration. `app/validation/` holds pure functions returning `Issue` lists. `services/orders.py` computes status. The repository layer always filters by `owner_id`. Turned down: a generic CRUD base class (too much indirection for 3 tables).

**Blast radius**
- Touches: API only
- Files to touch:
  - `app/models.py`: User, Document, Order, matching `docs/architecture/schema.sql` (the human-reviewed DDL)
  - `alembic/versions/0001_initial.py`
  - `app/security.py`: argon2id (argon2-cffi), JWT (PyJWT), `get_current_user` dependency
  - `app/routers/auth.py`: register, login (OAuth2 form), me
  - `app/routers/orders.py`: list (`status` filter, limit/offset), create, get, patch, delete
  - `app/schemas.py`: OrderCreate/OrderUpdate/OrderOut, IssueOut, UserOut, Token
  - `app/validation/{__init__,names,dob,npi,status}.py`
  - `app/services/orders.py`
  - `app/seed.py` + `make seed`: idempotent, parses `SEED_USERS="email:pw,email:pw"`, creates missing users, never updates or logs passwords
  - `app/ratelimit.py`: in-memory per-IP limit on `/auth/login` and `/auth/register` (10/min)
  - `services/api/railway.json`: pre-deploy `alembic upgrade head && python -m app.seed`
  - `tests/conftest.py` (test DB, client, user factory), `tests/test_auth.py`, `tests/test_orders.py`, `tests/test_validation.py`, `tests/test_seed.py`
- Also affected: OpenAPI schema (consumed by M4)
- Left alone: web app
- Rollback: `alembic downgrade base`

**Concerns:** None

**Security:**
- Data in and out: credentials in, a JWT out. Order PHI fields in and out
- Who can access it: authenticated owner only. Others get 404. Unauthenticated gets 401
- Stored: argon2id hashes, order fields. No plaintext passwords and no PHI in logs
- Abuse: credential stuffing → rate limit. ID enumeration → 404 and UUIDs. Mass assignment → explicit schemas (`owner_id` and `status` are never client-settable)

**Acceptance criteria**
- **Schema** (AC-M2.6): `make schema-diff` shows no difference between the migrated DB and `docs/architecture/schema.sql`. An IntegrityError never logs row values.
- **Register/login** (AC-M2.1): register returns 201. A duplicate email returns 409. Login returns a bearer token. A bad password returns 401. A password under 8 characters returns 422.
- **CRUD** (AC-M2.2): create → get → patch → list → delete round-trips are persisted, and a deleted order returns 404.
- **Isolation** (AC-M2.3): user B gets 404 on GET/PATCH/DELETE of A's order, and A's order never appears in B's list. No token returns 401.
- **Validation** (AC-M2.4): creating an order with NPI `9182734556` saves it as given, with error `npi.checksum_failed` and status `needs_review`. Patching it to a valid NPI (e.g. `1234567893`) with all other fields valid gives `ready`. A missing field gives `<field>.not_found`. A DOB in the future gives an error. A DOB from 1900 gives warning `dob.age_over_120` without blocking `ready`.
- **Seed** (AC-M2.5): `SEED_USERS` with two users creates both, and they can log in. Re-running the seed changes nothing and logs no passwords.

**How it will be proven:** pytest against compose Postgres · API smoke against the running app

**Size** L · ~650 lines · ~450k tokens · single PR

**Out of scope:** extraction, document upload (the model only), password reset

**Context:** none

---
## 2. Grill
See `docs/process/grill-log.md`. Seeded reviewers: decision log D20.

## 3. Design & architecture
### Contract
| Method | Path | Change | Breaking? |
| --- | --- | --- | --- |
| POST | /auth/register `{email,password}` → 201 `UserOut` | new | no |
| POST | /auth/login (form `username`,`password`) → `{access_token,token_type}` | new | no |
| GET | /auth/me → `UserOut` | new | no |
| GET | /orders?status=&limit=50&offset=0 → `{items: OrderOut[], total}` | new | no |
| POST | /orders `OrderCreate` (all 5 fields optional) → 201 `OrderOut` | new | no |
| GET/PATCH/DELETE | /orders/{id} | new | no |

`OrderOut`: `id, status, patient_first_name, patient_last_name, patient_dob, provider_name, provider_npi, issues[], extraction|null, document|null, created_at, updated_at`.

### Validation rules
See `docs/context/decisions/2026-11-04-validation-needs-review.md`. Names: trim and collapse whitespace; no digits; at most 100 characters. A PATCH re-runs every validator on the merged record. Extraction-time issues (`ungrounded`, multiple candidates) on a field are cleared once the user edits that field.

### Decisions
`2026-11-04-auth-api-jwt.md`, `2026-11-04-validation-needs-review.md`

## 4. Plan
### Tasks (one commit each, in order)
The builder commits after each task once its tests pass, with conventional messages:
1. `feat: add user, document and order models with initial migration` (must match `docs/architecture/schema.sql` exactly: constraints, composite FK, trigger)
2. `test: add schema-diff check against schema.sql` (`make schema-diff`: pg_dump of the migrated DB vs. the reviewed DDL)
3. `fix: log integrity errors by constraint name only` (never `str(exc)`; also set `log_error_verbosity=terse` on Railway's DB)
4. `feat: add npi, dob and name validators with unit tests`
5. `feat: add status derivation from issues`
6. `feat: add argon2 password hashing and jwt auth dependency`
7. `feat: add register, login and me endpoints with tests`
8. `feat: add owner-scoped order crud endpoints`
9. `test: add user isolation tests`
10. `feat: add auth rate limiting`
11. `feat: add idempotent reviewer seed from SEED_USERS`
12. `chore: run migrations and seed on railway pre-deploy`

### Tests to add
- `test_auth.py`: AC-M2.1. `test_orders.py`: AC-M2.2, AC-M2.3. `test_validation.py`: AC-M2.4, including the Luhn table (valid `1234567893`, invalid `9182734556`, 9 digits, a leading 3). `test_seed.py`: AC-M2.5
- `.claude/qa/api-smoke.json`: register, login, create, get-as-other-user → 404 (AC-M2.1–M2.3)

### Context
none

## 5. Evidence
## 6. Retro
## 7. Hand-off
