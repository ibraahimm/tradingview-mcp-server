# Lifecycle Spec — the Saudi wave **journey** (canonical, TASI-W1/TASI-W2 committed methodology)

**Status:** canonical contract. **Source of truth:** `.claude/commands/tasi-track.md` (methodology) +
`.claude/scripts/tasi-track.js` (`buildItems`) (behaviour). The research port
`research/backtest/tracker.py` is **conformed** to the JS via golden vectors
(`research/spec/lifecycle_vectors/`) and a live JS↔Python differential test
(`research.backtest.selftest_tracker`). This document is the human-readable record of *what* the
journey is and *which parts are original methodology vs. unavoidable backtest adaptation.*

The waves are **not** three independent screens — they are stages of **one journey per symbol**. This
spec governs the journey/state layer; the per-wave gate logic lives in `research/spec/rules.yaml`.

---

## 1. Scope — what is and isn't "original methodology"

The **committed** tracker is **TASI-W1/TASI-W2 only**. `tasi-track.md` and `tasi-track.js` (as committed)
ingest `source=TASI-W1|TASI-W2`, classify states `ACTIVE-TASI-W1 / ACTIVE-TASI-W2 / GRAD★ / FAILED / STALE / EXPIRED`, and
carry badges `NEW / PROMOTED / nearATH`. **There is no `ACTIVE-TASI-W3` in the committed methodology.**

> **TASI-W3-in-the-journey is an EXTENSION, not original methodology.** The Operational Handoff proposed
> TASI-W3 ingest (`source=TASI-W3`, an `ACTIVE-TASI-W3` state, an "expansion bridge") but it was **never committed**.
> This spec therefore implements the TASI-W1/TASI-W2 journey faithfully and treats any TASI-W3 lifecycle integration as
> a separate, clearly-labelled future increment — never silently folded into "the methodology."

## 2. The journey

Per symbol, roll all ledger **events** (one event = the name appeared in a wave screen on a date),
sorted by time. `first` = earliest event, `last` = latest.
- **`first_close` / `first_seen`** = the journey origin (stamped at ingest from the earliest prior event).
- **`gainSinceSignal` = (last.close / first_close − 1) × 100** — the headline progress metric (P&L since
  the *first* signal, **not** a fixed-horizon return).
- **`journey`** = the source path with consecutive duplicates collapsed (e.g. `TASI-W1→TASI-W2`).
- **`belowATH`** (from the last event) — structural recovery descriptor.

## 3. The state machine (precedence top-down — first match wins)

Evaluated with thresholds `grad_p5y=2000`, `stale_days=120`, `horizon_days=1826`, and clock `now`:

| Precedence | State | Condition |
|---|---|---|
| 1 | **FAILED** | `vs200 ≠ null` **and** `last.close < first_close` **and** `vs200 < 0` (underwater from the signal AND long trend broken). `vs200` = most-recent non-null reading (TASI-W2 events carry it; TASI-W1-only names can't FAIL). |
| 2 | **GRAD★** | `Perf.5Y > grad_p5y` (long-run big winner; kept & tracked). |
| 3 | **EXPIRED** | `ageDays > horizon_days` and not GRAD (`ageDays` from `first_seen`). |
| 4 | **STALE** | `sinceLast > stale_days` and not FAILED/GRAD (`sinceLast` from `last.date`). |
| 5 | **ACTIVE-TASI-W2 / ACTIVE-TASI-W1** | otherwise; suffix = `last.source`. |

**Badges** (orthogonal): `NEW` = `first_seen == latest run date`; `PROMOTED` = appeared in **both** TASI-W1 and
TASI-W2 (the TASI-W1→TASI-W2 progression); `nearATH` = `belowATH < 10`.

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
| **A6** | **TASI-W3 in the journey** | not present (TASI-W1/TASI-W2 committed). | not implemented here. | See §1 — kept out to avoid passing an extension off as original methodology. |

**Governing rule:** where the backtest has more information (A5) or denser observation (A2), it must
**collapse to the live tracker on the dates the live tracker actually observed**, and only add
resolution elsewhere. The state machine never changes.

## 5. Conformance (how we prove faithful, not just lookalike)

1. **Golden vectors** — `research/spec/lifecycle_vectors/{ledger.jsonl, params.json, expected.json}`.
   `expected.json` is emitted by the **live** `tasi-track.js stage=conform` (the source of truth);
   `_gen.py` regenerates the synthetic ledger. The vectors cover every state, the FAILED-over-GRAD
   precedence, and all three badges.
2. **Python == golden** and **hand-checked state meaning** — `research.backtest.selftest_tracker`.
3. **JS ↔ Python differential** — the same self-test runs the live `tasi-track.js` on the same ledger
   and asserts identical per-symbol output (same input → same output). Also verified on the **real**
   `.claude/outputs/saudi-tracker.jsonl` (25 symbols) during development.
4. CI-gated in `research-ci.yml` (with `node` available so the differential actually runs).

Faithfulness = (1)+(3): a shared executable contract **and** identical reproduction of the live tool —
explicitly **not** "produces similar-looking statistics."

## 6. Event-generation + historical replay (built on the proven state machine)

`research/backtest/replay.py` + `research/replay_run.py` generate ledger events from the engine's
TASI-W1/TASI-W2 pass-rows under the **daily-cadence** adaptation (A2/A4) and replay the journeys with the proven
tracker. Gated by `selftest_replay`. Two cadence artifacts to read carefully (they are ADAPTATION,
not documented methodology): under daily evaluation the **promotion rate is inflated** (almost any TASI-W1
name eventually also forms a TASI-W2 coil if you look every day — the live sparse tracker promotes far
less), and long-lived recurring names accumulate into **EXPIRED** journeys (the journey never resets).
Compare today's live tracker to the historical journey *shapes* (promoted reach higher peak gains;
FAILED are falling knives), not to the cadence-inflated rates directly.
