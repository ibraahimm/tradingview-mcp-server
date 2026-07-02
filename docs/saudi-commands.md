# Saudi Main Market Command Registry (index)

Reusable Claude Code slash commands scoped to the **Saudi Main Market (TADAWUL) only** — on-demand,
pulling live data on each run. **The authoritative spec for each command is its file in
[`.claude/commands/`](../.claude/commands/); this page is a thin index and restates none of their
parameters, defaults, or logic.**

**Universe restriction (every command):** TADAWUL main-board listed **stocks** only, never substituted
from other markets; Nomu/parallel-market `9xxx`, ETFs, and REITs/funds (`REIT`/`Fund`/`ETF`/`Sukuk`)
excluded.

| Command | Purpose | Authoritative spec |
|---|---|---|
| `/saudi-stage2` | **TASI-W1** — deep multi-year correction + first recovery wave (entry) | [`.claude/commands/saudi-stage2.md`](../.claude/commands/saudi-stage2.md) |
| `/saudi-wave2`  | **TASI-W2** — first EMA coil + continuation of TASI-W1 names | [`.claude/commands/saudi-wave2.md`](../.claude/commands/saudi-wave2.md) |
| `/saudi-wave3`  | **TASI-W3** — mature re-coil near new highs | [`.claude/commands/saudi-wave3.md`](../.claude/commands/saudi-wave3.md) |
| `/saudi-track`  | Unified TASI-W1/TASI-W2 journey tracker (read-only) | [`.claude/commands/saudi-track.md`](../.claude/commands/saudi-track.md) |
| `/saudi-momentum` | Rising off the 52-week low in a tight, confirmed uptrend | [`.claude/commands/saudi-momentum.md`](../.claude/commands/saudi-momentum.md) |

**Canonical rule thresholds** for the wave screens (TASI-W1/TASI-W2/TASI-W3) live in
[`research/spec/rules.yaml`](../research/spec/rules.yaml); their change history in
[`research/spec/decisions.md`](../research/spec/decisions.md). (`/saudi-momentum` predates the wave
system and is not in canon — its parameters are owned solely by its command file.)

**Adding a command:** create `.claude/commands/<name>.md` (frontmatter `description:` + instructions),
then add one row above — a link, not a copy of its contents.
