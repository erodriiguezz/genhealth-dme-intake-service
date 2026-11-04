# How this project was built

This repo was built AI-natively: a lead agent (Claude Opus) planned, questioned the human and reviewed every change, and builder agents (Claude Sonnet) wrote the code. The human approved the design before any code was written. This folder is the audit trail.

| File | What it holds |
|------|---------------|
| [assignment.md](assignment.md) | The take-home brief, restated as requirements R1–R9 |
| [grill-log.md](grill-log.md) | Every question the planning agent asked, the options it offered with its recommendation, and the human's answer, round by round |
| [decision-log.md](decision-log.md) | Every decision in time order: who decided, why, and which ADR covers it |
| [timeline.md](timeline.md) | Timestamped milestones of the 3-hour timebox |
| `sessions/` | Exported agent session transcripts (added at the end) |

Related:

- `.claude/plans/`: the MVP plan and the per-milestone plans the agents built from (acceptance criteria `AC-*`)
- `docs/context/`: product, architecture, domain and status tables
- `docs/context/decisions/`: ADRs, one per real technical choice
- `docs/context/designs/`: UI design notes and wireframes
- `docs/reviews/`, `docs/evidence/`: how to review each PR and the test evidence behind it
