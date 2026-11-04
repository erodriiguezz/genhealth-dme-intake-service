## v<version> · YYYY-MM-DD
Decisions: what we chose, each linked to its ADR
Turns: where we changed course, and what made us change
Dropped: ideas tried or rejected, and why
Debt taken on: shortcuts to pay back later
Open questions: still undecided

### Scorecard
| Issue | Size | Est. tokens | Actual tokens | Ratio | Est. lines | Actual lines | Test runs | Blocking findings | @claude fixes | Rating |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| #<n> | S/M/L | | | | | | | | | x.x / 5 |

Rating evidence: one line per issue — estimate accuracy · first-pass quality · review outcome · rework · plan accuracy.

### Delivery metrics (`node scripts/sdlc/metrics.mjs --md`)
| Metric | Stage | This release | Previous | Target |
| --- | --- | --- | --- | --- |
| Lead time for changes (first commit → merged, median) | all | | | trending down |
| Change failure rate (PRs followed by a hotfix/revert within 14 days) | Release | | | < 15% |
| Escaped defects (bugs linked to this release's issues within 14 days) | Test | | | < 10% of issues |
| Gate coverage (merged PRs with required checks run) | Review | | | 100% |
| Gate flake rate (check reruns that passed with no new commit) | Review | | | < 5% |
| Evidence completeness (merged PRs with docs/evidence/<issue>.json) | all | | | 100% |

Weakest stage: <stage> — next process change goes here.

### Calibration (last 3 releases)
| Size | Avg est. tokens | Avg actual tokens | Ratio | Hand-offs |
| --- | --- | --- | --- | --- |
| S | | | | x of n |
| M | | | | |
| L | | | | |

Proposed token-estimate changes for .claude/sdlc.json: none / …

### Lessons → changes (see docs/context/lessons.md)
- L<n> <lesson> (seen <x>×) → <process PR link> | watching | dropped: <reason>
- Adopted earlier: did they move the numbers they targeted?
