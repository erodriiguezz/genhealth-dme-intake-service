# Assignment: GenHealth Full Stack AI Engineer take-home

Source: "Full Stack AI Engineer – Take-home assessment" (PDF, received 2026-11-04). The PDF is not committed; its requirements are restated below.

**Context:** DME suppliers get faxed or scanned order PDFs from doctors' offices, and a person keys the patient and provider details in by hand. A wrong value means a denied claim or a delayed patient. Build a small order-intake service the way an AI-native team would.

| ID | Requirement |
|----|-------------|
| R1 | Python REST API with CRUD on an `Order`, persisted to a database |
| R2 | Accept an uploaded PDF and extract the patient's first name, last name and DOB, plus the ordering provider's name and NPI. It will be tested with unseen PDFs, including scanned faxes and messy multi-page documents |
| R3 | Check extracted values before saving. Don't guess when a field is missing |
| R4 | Authentication: each user sees only their own orders |
| R5 | Deployed and reachable at a public endpoint, with a working document upload endpoint (hard gate) |
| R6 | API in Python. Any frontend in JS/TS |
| R7 | Secrets (API keys) kept out of the repo |
| R8 | Commit as you go, so the git history can be followed |
| R9 | Timebox: 3 consecutive hours at most |

Plus "whatever else a production-ready MVP needs".

**Deliverable:** public URL and repo link (or a zip that includes `.git`), emailed to the reviewers at the end of the timebox.

**Next stage:** a 90-minute pair-programming session making a small change to this project with AI. So the codebase must be easy to change, and the context docs must be good enough for an agent to pick up.
