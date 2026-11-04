# Decision journal

Two kinds of file:

- **`<issue>-<slug>.md`**, written by the builder when the plan's Context table has rows, from `ENTRY.md`. One new file per such change. The plan says `none` when no row changes, and then this file is not written.
- **`<version>.md`**, written by `/release` from `TEMPLATE.md`. One file per release: decisions, scorecard, delivery metrics. It links the per-issue entries instead of copying them.
