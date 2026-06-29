# Lifecycle Spec — the Saudi wave **journey** (canonical, W1/W2 committed methodology)

**Status:** canonical contract. **Source of truth:** `.claude/commands/saudi-track.md` (methodology) +
`.claude/scripts/saudi-tracker.js` (`buildItems`) (behaviour). The research port
`research/backtest/tracker.py` is **conformed** to the JS via golden vectors
(`research/spec/lifecycle_vectors/`) and a live JS↔Python differential test
(`research.backtest.selftest_tracker`). This document is the human-readable record of *what* the
journey is and *which parts are original methodology vs. unavoidable backtest adaptation.*

The waves are **not** three independent screens — they are stages of **one journey per symbol**. This
spec governs the journey/state layer; the per-wave gate logic lives in `research/spec/rules.yaml`.

---

## 1. Scope — what is and isn't "original methodology"

The **committed** tracker is **W1/W2 only**. `saudi-track.md` and `saudi-tracker.js` (as committed)
ingest `source=W1|W2`, classify states `ACTIVE-W1 / ACTIVE-W2 / GRAD★ / FAILED / STALE / EXPIRED`, and
carry badges `NEW / PROMOTED / nearATH`. **There is no `ACTIVE-W3` in the committed methodology.**

> **W3-in-the-journey is an EXTENSION, not original methodology.** The Operational Handoff proposed
> W3 ingest (`source=W3`, an `ACTIVE-W3` state, an "expansion bridge") but it was **never committed**.
> This spec therefore implements the W1/W2 journey faithfully and treats any W3 lifecycle integration as
> a separate, clearly-labelled future increment — never silently folded into "the methodology."

## 2. The journey

Per symbol, roll all ledger **events** (one event = the name appeared in a wave screen on a date),
sorted by time. `first` = earliest event, `last` = latest.
- **`first_close` / `first_seen`** = the journey origin (stamped at ingest from the earliest prior event).
- **`gainSinceSignal` = (last.close / first_close − 1) × 100** — the headline progress metric (P&L since
  the *first* signal, **not** a fixed-horizon return).
- **`journey`** = the source path with consecutive duplicates collapsed (e.g. `W1→W2`).
- **`belowATH`** (from the last event) — structural recovery descriptor.

## 3. The state machine (precedence top-down — first match wins)

Evaluated with thresholds `grad_p5y=2000`, `stale_days=120`, `horizon_days=1826`, and clock `now`:

| Precedence | State | Condition |
|---|---|---|
| 1 | **FAILED** | `vs200 ≠ null` **and** `last.close < first_close` **and** `vs200 < 0` (underwater from the signal AND long trend broken). `vs200` = most-recent non-null reading (W2 events carry it; W1-only names can't FAIL). |
| 2 | **GRAD★** | `Perf.5Y > grad_p5y` (long-run big winner; kept & tracked). |
| 3 | **EXPIRED** | `ageDays > horizon_days` and not GRAD (`ageDays` from `first_seen`). |
| 4 | **STALE** | `sinceLast > stale_days` and not FAILED/GRAD (`sinceLast` from `last.date`). |
| 5 | **ACTIVE-W2 / ACTIVE-W1** | otherwise; suffix = `last.source`. |

**Badges** (orthogonal): `NEW` = `first_seen == latest run date`; `PROMOTED` = appeared in **both** W1 and
W2 (the W1→W2 progression); `nearATH` = `belowATH < 10`.

## 4. Live ↔ backtest adaptations — ORIGINAL vs ADAPTATION (read this carefully)

The state machine above is **identical** in the live tool and the research port. The differences below
are confined to **(a) the clock and (b) the future event-GENERATION layer** — never the state logic.

| # | Aspect | Original (live tool) | Backtest adaptation | Why unavoidable / how kept faithful |
|---|---|---|---|---|
| **A1** | **Clock** | `now = Date.now()` (wall-clock) | `now = as_of` (a date) | Replaying history needs a point-in-time clock. **Identical when `as_of = today`.** This is the *only* adaptation inside the state machine. |
| **A2** | **Observation cadence** | An event exists only on days the user **actually ran** the screen — sparse, irregular, human-driven. | Canonical replay = **screen evaluated every trading day**; an event = each trading day a wave's gate passes. | The backtest can't know the human's run schedule, so it assumes the *idealised* "could have been run any day." The live ledger is a **sparse sample** of this. A coarser cadence (weekly/monthly) is available only as an explicit **sensitivity**, not the canonical replay. |
| **A3** | **`runs` & `sinceLast` meaning** | `runs` = number of *runs* the name appeared in; `sinceLast` = days since the last *run* that surfaced it. | Under daily cadence, `runs` = number of *days the gate passed*; `sinceLast` = days since the gate **last passed**. | Direct consequence of A2. **STALE semantics become *gate-driven*** ("the setup stopped qualifying for >120 days") instead of *usage-driven* ("the user didn't re-run") — arguably **more faithful to the intent** ("dropped off the radar"), and stated explicitly so the two are never conflated. |
| **A4** | **`first_seen`** | first run-day the name happened to be caught. | first trading day the gate passes (deterministic). | Same definition under daily cadence; removes dependence on when the user happened to run it. |
| **A5** | **Data snapshot & delisting** | last/most-recent live reading; delisted names dangle unresolved. | PIT adjusted vintage + curated **delisting terminal values**; delisted journeys are resolved. | The backtest is a **faithful superset**: it must reproduce the live state on the dates the live tracker observed, and may only *add* resolution elsewhere — never contradict it. |
| **A6** | **W3 in the journey** | not present (W1/W2 committed). | not implemented here. | See §1 — kept out to avoid passing an extension off as original methodology. |

**Governing rule:** where the backtest has more information (A5) or denser observation (A2), it must
**collapse to the live tracker on the dates the live tracker actually observed**, and only add
resolution elsewhere. The state machine never changes.

## 5. Conformance (how we prove faithful, not just lookalike)

1. **Golden vectors** — `research/spec/lifecycle_vectors/{ledger.jsonl, params.json, expected.json}`.
   `expected.json` is emitted by the **live** `saudi-tracker.js stage=conform` (the source of truth);
   `_gen.py` regenerates the synthetic ledger. The vectors cover every state, the FAILED-over-GRAD
   precedence, and all three badges.
2. **Python == golden** and **hand-checked state meaning** — `research.backtest.selftest_tracker`.
3. **JS ↔ Python differential** — the same self-test runs the live `saudi-tracker.js` on the same ledger
   and asserts identical per-symbol output (same input → same output). Also verified on the **real**
   `.claude/outputs/saudi-tracker.jsonl` (25 symbols) during development.
4. CI-gated in `research-ci.yml` (with `node` available so the differential actually runs).

Faithfulness = (1)+(3): a shared executable contract **and** identical reproduction of the live tool —
explicitly **not** "produces similar-looking statistics."

## 6. What this increment does NOT do (next increment)

This delivers the faithful **tracker-on-a-ledger**. It does **not** yet generate the ledger from the
historical panel (the daily-cadence event-GENERATION layer, A2/A4), nor re-point the research
evaluation onto journey outcomes. Those are the next increment, built on this proven state machine.
