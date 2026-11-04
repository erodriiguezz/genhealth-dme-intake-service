# Decision log

Every decision in time order. Technical choices with real tradeoffs get an ADR in `docs/context/decisions/`.

| # | Date | Decision | Decided by | Why | ADR |
|---|------|----------|------------|-----|-----|
| D1 | 2026-11-04 | Monorepo: Next.js (TypeScript) frontend + Python REST API service | Human | Stated in the kickoff; matches R6 | _pending_ |
| D2 | 2026-11-04 | All planning artifacts (grill Q&A, decisions, plans, ADRs, designs, transcripts) are committed to the repo | Human | The reviewers should be able to see how the work was done, not just the result | n/a |
| D3 | 2026-11-04 | Don't run the Python API on Vercel serverless | Agent | Its 4.5 MB body limit breaks multi-page scanned PDF uploads (R2, R5) | _pending_ |
| D4 | 2026-11-04 | Don't commit the assignment PDF. Restate it as `docs/process/assignment.md` | Agent | Keeps the reviewer's document out of a possibly public repo while keeping the requirements traceable | n/a |
| D5 | 2026-11-04 | Extraction through the Anthropic API (Claude reads the PDF natively), behind a provider interface so Bedrock is a config swap | Human (agent recommended) | Most robust on unseen scanned faxes. The swap path covers production HIPAA (BAA) | _pending_ |
| D6 | 2026-11-04 | Default extraction model `claude-opus-5-5`, set by env var | Human (agent recommended) | Accuracy over cost: a wrong value means a denied claim. About $0.09 per 5-page doc | _pending_ |
| D7 | 2026-11-04 | Missing or invalid fields are saved as null with an issues list. The order is `needs_review` until every field validates | Human (agent recommended) | R3: never guess, and don't throw away the fields that were extracted correctly | _pending_ |
| D8 | 2026-11-04 | Auth owned by the API: email + argon2 password, JWT bearer, every query scoped by owner | Human (agent recommended) | R4. Graders can test with curl or Swagger without any third-party signup | _pending_ |
| D9 | 2026-11-04 | Hosting: Vercel (web) + Railway (API + Postgres) | Human (overrode the agent's Render + Neon recommendation) | One platform for the API and DB, fast deploys | _pending_ |
| D10 | 2026-11-04 | PHI posture: synthetic data only in the demo, PHI-ready code, BAAs listed as a production prerequisite | Agent, after the human raised HIPAA | No free-tier vendor signs a BAA. The design keeps the path to compliance open | _pending_ |
| D11 | 2026-11-04 | Store uploaded PDFs (owner-scoped) so the review UI can preview them | Human (overrode the agent's discard recommendation) | The review UI shows the source next to the extracted fields | _pending_ |
| D12 | 2026-11-04 | PDF preview is the last milestone, cut if not started by 14:30 | Human (agent recommended) | Protects the deploy and proof inside the 15:13 hard stop | n/a |
| D13 | 2026-11-04 | Eval: the GenHealth CPAP fax as benchmark plus a synthetic set (clean, noisy/rotated scan, multi-page, missing field, invalid NPI, handwritten-style) | Human (agent recommended) | R2 is tested on unseen PDFs | _pending_ |
| D14 | 2026-11-04 | Synchronous extraction in the upload request. Async job + polling documented as the scaling path | Human (agent recommended) | Simplest thing graders can curl. Async adds a worker plus ~30 minutes | _pending_ |
| D15 | 2026-11-04 | PDFs stored as Postgres bytea in an owner-scoped `documents` table. S3 is the documented scaling path | Human (agent recommended) | One datastore, no extra credentials | _pending_ |
| D16 | 2026-11-04 | A present-but-invalid value is stored exactly as read and flagged with an error issue | Human (agent recommended) | The reviewer sees what the document says, and nothing is invented (R3) | _pending_ |
| D17 | 2026-11-04 | NPPES registry verification goes on the backlog, done only if time remains | Human | Timebox | n/a |
| D18 | 2026-11-04 | E2E browser proof: upload→review→fix→ready, user isolation, missing-field upload | Human | Covers R2–R4 in the UI. CRUD is covered by API tests | n/a |
| D19 | 2026-11-04 | Remote repo: github.com/erodriiguezz/genhealth-dme-intake-service (public, created empty by the human) | Human | Graders follow the history and PRs there | n/a |
| D20 | 2026-11-04 | Seed reviewer accounts mahum@genhealth.ai and mike@genhealth.ai with an idempotent seed command reading `SEED_USERS` from the env (Railway variable). Passwords never committed; the human sends them in the submission email. Open registration stays | Human (passwords-in-env design: agent) | Reviewers log straight in, and two accounts give a built-in isolation test. R7 keeps the passwords out of the public repo | n/a |
| D21 | 2026-11-04 | Milestone plans written with the Write tool after secret-guard blocked a heredoc whose plan text mentioned an env-file path (nothing secret was read) | Human ("do it") | False positive on path text. Not a secret access | n/a |
| D22 | 2026-11-04 | Commit after every completed task inside a milestone. Milestone PRs merged with merge commits (no squash), so task history reaches `main` | Human | R8: graders follow the git history | n/a |
| D23 | 2026-11-04 | In-depth docs: `docs/architecture/{architecture,data-schema,api}.md` | Human | Depth for reviewers and the pair session | n/a |
| D24 | 2026-11-04 | UI prototype as a Claude artifact, signed off before M4. Built during planning so the chain doesn't stop | Human (timing: agent) | Finalize the UI before code | n/a |
| D25 | 2026-11-04 | No GenHealth logo or name as product branding. Inspired-by palette and type with a 'not an official product' footer is proposed | Agent (pending the human's answer) | Impersonation and phishing risk on a public login page | n/a |
| D26 | 2026-11-04 | Visual language inspired by genhealth.ai's public CSS: blue #0648C0, ink #0B0D10, paper #EEEEF1, mint/yellow/red accents, Lexend + Marcellus + JetBrains Mono (Google Fonts). No logo, no GenHealth product name, disclaimer footer on every page | Human (option a, agent proposed) | Fits their product line without impersonating it | n/a |
| D27 | 2026-11-04 | UI prototype signed off as M4's design source | Human ("ui looks good and it's approved") | Design locked before code | n/a |
| D28 | 2026-11-04 | Full DDL in docs/architecture/schema.sql (human review). Tested on postgres:16. NPI column widened to varchar(20). Composite owner FK. DB-level ready guard. PHI-safe IntegrityError logging + log_error_verbosity=terse | Agent, for the human's review | Found while testing: PG error DETAIL leaks row values | n/a |
| D29 | 2026-11-04 | Re-plan at 13:50 (M1 in PR #1): parallel lanes. Wave 1 is M2 (A), M3a extraction core (B) and M4 UI (C) from M1 head. Wave 2 is M3b wire-up. Wave 3 is M6. M5 cut to backlog B9. Freeze at 14:55 | Agent (awaiting the human's approval) | 1h23 left vs ~2h sequential. Lanes own disjoint files | n/a |
| D30 | 2026-11-04 | MVP plan + M2, M3 (a/b), M4, M6 approved as re-planned. M5 marked cut | Human ("approve and deliver") | Launch wave 1 | n/a |
