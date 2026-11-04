# ADR: HIPAA posture: synthetic data only, PHI-ready design

- Date: 2026-11-04
- Status: proposed
- Issue / PR: MVP order-intake (D10, raised by the human in grill round 1)

## Context
Real DME orders contain PHI. Any vendor that processes or stores PHI needs a Business Associate Agreement (BAA). That covers the LLM, the API host, the database and the frontend host, not just the LLM.

## Decision
- **The demo uses only synthetic or sample documents.** The deployed app shows a banner saying not to upload real PHI.
- **The code is PHI-ready:**
  - no PHI in logs (structured logs carry IDs, field names, issue codes and latency, never values)
  - TLS everywhere
  - owner-scoped access, with 404 for other users' resources
  - the PDF is served with `no-store`
  - the LLM provider sits behind the `Extractor` interface
- **Production prerequisites (not done):**
  - a BAA with Anthropic (with zero data retention), or extraction moved to AWS Bedrock under an AWS BAA
  - BAA-covered hosting and DB (e.g. AWS App Runner/ECS + RDS)
  - an audit log of PHI access
  - encryption at rest with managed keys
  - retention and deletion policy

## Consequences
The free and hobby tiers used here (Vercel, Railway) are not BAA-covered. That's acceptable for synthetic data only.
