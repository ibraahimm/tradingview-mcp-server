# /saudi-track — Saudi Wave Cohort Tracker (read-only report)

Show the **unified journey** of every name surfaced by `/saudi-stage2` (W1, "first wave") and
`/saudi-wave2` (W2, "second wave / continuation"), accumulated in a persistent append-only
ledger. One journey per symbol across both waves: a name can first appear in W1, later in W2,
and the tracker treats that as one continuous journey.

This command is **read-only** — it only renders the current ledger. The ledger itself is written
by the **optional ingest step** inside `/saudi-stage2` and `/saudi-wave2` when those run. If the
ledger doesn't exist yet, run one of those first.

## Architecture (read first)

Orchestration only. All lifecycle math + formatting live in the persistent helper:

```
.claude/scripts/saudi-tracker.js      (stage=report)
.claude/outputs/saudi-tracker.jsonl   (the append-only JSONL ledger — source of truth)
```

> Script invocation: the project is ESM (`"type":"module"`), so run with `node …` as shown.

## Parameters

Parse `` for `key=value` tokens; forward to the script (it owns the defaults):

| Key            | Default | Meaning |
|----------------|---------|---------|
| `grad_p5y`     | `2000`  | Graduation flag: `Perf.5Y > grad_p5y` (the long-run big-winner flag) |
| `stale_days`   | `120`   | Mark STALE if not seen on either screen for this many days |
| `horizon_days` | `1826`  | ~5-year journey horizon; older non-graduated names → EXPIRED |
| `csv`          | (none)  | Optional path to also export the per-symbol summary as CSV |
| `ledger`       | `.claude/outputs/saudi-tracker.jsonl` | Ledger path (leave default) |

Example calls:
- `/saudi-track`
- `/saudi-track csv=.claude/outputs/saudi-tracker-summary.csv`
- `/saudi-track stale_days=60`

## Steps

1. **Parse parameters** from `` into `key=value` tokens.

2. **Run the report stage**:
   ```
   node .claude/scripts/saudi-tracker.js stage=report grad_p5y=<grad_p5y> stale_days=<stale_days> horizon_days=<horizon_days> [csv=<csv>]
   ```
   (Omit any token the user didn't supply — the script applies its own defaults.)

3. **Print the output.** Stdout has **two parts separated by a line that is exactly
   `===CHART_LINKS===`**:
   - **Before the sentinel** — the tracker header, the **box-grid journey table** (sorted by
     `gainSinceSignal` descending), and the **state/badge summary**. **Print this whole part as-is
     inside a fenced ```text code block.** Columns (fixed order): `Sym Name First Jrny Rns Entry
     Now Gain% bATH offL 5Y v200 State`. `Jrny` is the W1/W2 path (e.g. `W1→W2`); `Gain%` is
     `close/first_close − 1`; `State` ∈ `ACTIVE-W1 | ACTIVE-W2 | GRAD★ | FAILED | STALE | EXPIRED`.
     Do NOT convert to a Markdown/ASCII table and do NOT split it.
   - **After the sentinel** — a markdown "**Open chart (click a symbol)**" list. **Print as normal
     markdown OUTSIDE the code block.** Do not print the `===CHART_LINKS===` line itself.
   - If the ledger is empty, the script prints a "No tracker ledger yet" message — surface that
     and tell the user to run `/saudi-stage2` or `/saudi-wave2` first.

4. **No cleanup, no live fetch.** This command reads only the persistent ledger; it creates no
   temp files and calls no MCP tools.

## Lifecycle reference

- **FAILED** — latest EMA reading shows `close < first_close` AND `close < EMA200` (underwater from
  the original signal AND long trend broken). W1-only names (no EMA data) can't be FAILED yet.
- **GRAD★** — `Perf.5Y > grad_p5y` (default 2000). The name is kept and tracked.
- **EXPIRED** — older than `horizon_days` since first seen and not graduated.
- **STALE** — not seen on either screen for `> stale_days`.
- **ACTIVE-W1 / ACTIVE-W2** — still appearing; suffix is the most recent wave.
- Badges (in summary): **NEW** (first appeared in the latest run), **PROMOTED** (appeared in both
  W1 and W2 — the W1→W2 progression), **near-ATH** (belowATH < 10%, descriptor).
- Progress metrics: `gainSinceSignal = close/first_close − 1` (main), `belowATH` (structural recovery).
