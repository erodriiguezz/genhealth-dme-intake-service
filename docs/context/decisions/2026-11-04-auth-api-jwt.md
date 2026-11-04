# ADR: API-owned email/password auth with JWT bearer tokens

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D8)

## Context
R4: authentication, and each user sees only their own orders. Graders will call the API directly (curl, Swagger) as well as through the UI.

## Options
1. **FastAPI-owned auth:** `POST /auth/register` and `POST /auth/login` (OAuth2 password flow), argon2id hashes, HS256 JWT valid for 60 min. No vendor, and it works in Swagger's Authorize button.
2. **Clerk.** Polished hosted UI, but API calls need a Clerk-issued JWT, which graders can't easily get.
3. **Supabase Auth.** Same friction as Clerk, plus an extra SDK.

## Decision
Option 1. Every repository query is filtered by `owner_id = current_user.id`. Another user's resource returns **404** (not 403), so IDs can't be enumerated. The JWT secret comes from `JWT_SECRET` (Railway variable) and is never committed. Login is rate-limited in memory per IP.

## Consequences
- No password reset, email verification or refresh tokens in the MVP (backlog).
- The web app keeps the token in `sessionStorage` and sends it as `Authorization: Bearer` (see the frontend ADR).
