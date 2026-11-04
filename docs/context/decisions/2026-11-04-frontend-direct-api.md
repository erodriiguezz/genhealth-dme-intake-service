# ADR: The web app calls the API directly with a bearer token

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake

## Context
Uploads can exceed 4.5 MB, which is Vercel's function body limit, so they can't go through a Next.js route handler proxy (a BFF).

## Options
1. **BFF proxy with an httpOnly cookie.** Best token hygiene, but uploads over 4.5 MB fail.
2. **Browser → API directly**, with a JWT in `sessionStorage` sent as a bearer header, and CORS limited to the web origin.

## Decision
Option 2. Short-lived tokens (60 min), cleared on logout and tab close. No third-party scripts. A strict CSP is set in `next.config`. A 401 redirects to `/login`.

## Consequences
- A token in `sessionStorage` can be read by XSS. The mitigations are the CSP, React escaping and no `dangerouslySetInnerHTML`. Revisit with a same-site API domain plus an httpOnly cookie in production.
