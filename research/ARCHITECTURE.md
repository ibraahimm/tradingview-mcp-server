# Tadawul Quant Research & Backtesting Platform — Architecture

**Status:** Draft v0.1 · 2026-06-27
**Scope.** This is the home of **system-wide / cross-cutting rationale** for the whole
repository — its three subsystems and how they fit together:
1. the **TradingView MCP server + CLI** (`src/`) — the market-data screener the product trades on;
2. the **live Saudi wave-screening product** (`.claude/commands/` + `.claude/scripts/`) —
   `/saudi-stage2` (W1), `/saudi-wave2` (W2), `/saudi-wave3` (W3), `/saudi-track`;
3. the **quant research & backtesting platform** (`research/`) — this document's most detailed
   subject, plus the continuous conformance contract with the live screener those strategies trade on.

**Rationale boundary (see [`/DOCUMENTATION.md`](../DOCUMENTATION.md) §5, and its D6 rule).**
System and cross-subsystem rationale live *here*. Rationale **local** to one directory lives in
that directory's `README.md`, which **links up** to this document rather than re-explaining the
whole; a local README never restates a global decision. The rest of the document below details
subsystem 3 (the research platform); subsystems 1–2 are documented operationally in their own
directories and depend on the same canon and conformance contracts described here.

This document records **what** we build, **why**, **what alternatives were considered**,
and **what trade-off** each decision accepts. It is the foundation the implementation works
from; when code and this document disagree, this document is wrong and should be fixed.

---

## 0. Why this platform exists (the problem statement)

The live system is a **snapshot** screener: the TradingView scanner returns today's `close`,
`EMA21`, `Perf.3M`, `DDmax`, etc., with no price history. Every attempt to validate or tune a
screen rule on that data is therefore either (a) reconstructed from a single snapshot under
strong assumptions, or (b) accumulated forward one day at a time. Both are inadequate:

- A reconstruction-from-snapshot "backtest" produced **n=15, one cohort, 6 days** and was
  fatally contaminated by look-ahead — a candidate gate (`ext60_max`) looked predictive only
  because the feature was read *after* the move it was "predicting."
- Forward accumulation is sound but **too slow** — years to reach a statistically usable sample.

We need a **survivorship-free, point-in-time historical panel** over the strategy's own universe
and features, so any rule can be evaluated at every historical bar with forward-return labels,
and validated **out-of-sample** instead of fit to one cohort.

**Non-goals (today):** intraday data, fundamentals-based gates, multi-market coverage, live
order execution. The design leaves clean seams for each (§13) but does not build them now.

---

## 1. Design principles (the load-bearing ideas)

1. **Three separate truths, never collapsed into one** (§2). The biggest conceptual error to
   avoid is treating TradingView as "ground truth." It is the *execution* reference, not the
   *correctness* reference.
2. **As-of or it doesn't ship.** Every value at bar *t* uses only information available at *t*.
   Look-ahead is the default failure mode of market backtests and the specific bug that ruined
   the first analysis; the architecture is built to make it structurally hard (§8).
3. **One canonical feature definition, executable.** A prose spec drifts. The spec is a
   versioned set of golden input→output vectors that *both* implementations must pass (§5, §6.4).
4. **Pragmatic to the market's size.** TADAWUL is ~300 names ever. That smallness is a gift: it
   makes a *hand-curated* point-in-time reference table the highest-fidelity *and* most feasible
   option, and it makes Parquet+DuckDB more than enough. We deliberately do **not** buy
   enterprise infrastructure the strategy can't use.
5. **Reproducible by construction.** Every backtest result pins its data vintage, spec version,
   universe-table version, and code commit. A result you can't reproduce is an anecdote.
6. **The human is the overfitting risk.** Once the backtest is fast, the dominant danger shifts
   from data quality to undisciplined iteration. Research governance is a first-class component
   (§7), not an afterthought.

---

## 2. The three-truths model (conceptual core)

| Truth | Role | Authority |
|---|---|---|
| **Canonical feature spec** | Defines what each indicator/rule *means* | **Wins all semantic conflicts.** Source of truth for research. |
| **Vendor historical panel** | What actually happened, survivorship-free | Source of truth for *history* (substrate the backtest runs on). |
| **TradingView live screener** | What we actually trade on | Execution reference + a **monitored, bounded delta** — *not* matched to zero. |

**Why this matters.** The intuitive design ("make our engine match TradingView") is wrong on two
counts: TV is **not static** (it restates history when corporate actions apply retroactively;
EMA values shift as bars print; it revises data), so it is a moving target; and TV is **not
correct-by-definition** (its EMA seeding, performance-window conventions, and adjustment method
are *choices*). Driving the engine to match TV to zero would (a) chase a moving target, (b)
**import TV's quirks into the backtest**, and (c) conflate "matches what we trade" with "is
correct."

**Consequence for conformance (§9):** we monitor the *stability* of the engine↔TV delta, not its
absence. A constant 0.3% EMA gap from a different adjustment convention is fine forever; a *jump*
in that gap is the alarm. When canonical spec and TV disagree, **spec wins** and the delta is
documented, not "fixed."

**Alternative considered:** single source of truth (use TV-derived history for everything). Rejected
— it bakes in survivorship bias (no delisted names) and adjustment opacity, the two worst sins for
this use case. Retained only as a *secondary* historical cross-check (§6.6).

---

## 3. System overview

```
                          ┌───────────────────────────────────────────────┐
                          │            THREE TRUTHS (governance)           │
                          │  spec ── wins ──►  vendor panel   TV (delta)   │
                          └───────────────────────────────────────────────┘

  L0 SOURCES        Vendor EOD (adj OHLCV, splits/divs, DELISTED)   TV live   TV history (1×)
                            │                                          │            │
                            ▼                                          │            │
  L1 INGEST + QA    raw immutable dump → quality checks ──────────────┐│            │
                            │                                         ││            │
  L2 PIT REFERENCE  hand-curated universe & corporate-action table    ││            │
                    (sec_id, list/delist+reason, board, type, CA)     ││            │
                            │                                         ││            │
  L3 FEATURE ENGINE Python/Polars; canonical spec; AS-OF indicators ◄─┘│            │
                            │   (golden-vector conformance in CI)       │            │
                            ▼                                           │            │
  L4 PANEL STORE    Parquet (partition by sec_id) ◄─ DuckDB query layer │            │
                            │                                           │            │
  L5 BACKTEST       (a) event-study   (b) portfolio sim (vectorbt)      │            │
                            │                                           │            │
  L6 VALIDATION     forward oracle (daily TV capture) ◄─────────────────┘            │
                    + one-time historical reconciliation ◄──────────────────────────┘
                            │                  + cross-vendor agreement
  L7 GOVERNANCE     experiment tracking · holdout · walk-forward · deflated metrics
  L8 PROVENANCE     run manifest pins {data vintage, spec ver, universe ver, commit}
```

---

## 4. Layer-by-layer decisions

### L0 — Data sources

**Decision.** Three inputs, each with a distinct job:
1. A **survivorship-free EOD vendor** for adjusted daily OHLCV + splits/dividends, **including
   delisted .SR names**, as the historical backbone.
2. A **hand-curated point-in-time reference table** (L2) as the authoritative universe &
   corporate-action source — *not* derived from the price vendor.
3. **TradingView** in two modes: the *live* screener (production + forward oracle) and a *one-time*
   full-history pull (historical reconciliation).

**Why split the price vendor from the reference data.** Price vendors are good at prices and weak at
point-in-time *classification* and *delisting reasons* — exactly the metadata that determines
survivorship correctness. Coupling them forces you to trust the vendor on the thing it's worst at.

**Vendor selection criteria (validate before committing):** delisted TADAWUL coverage with history
through the 2006 cycle; adjusted series with split/dividend events; stable identifiers. Candidate
classes: Saudi-covering EOD vendors (cheap, must verify delisted depth); enterprise point-in-time
(Refinitiv/Bloomberg/FactSet — gold standard but overkill for a price-only single market); official
Saudi Exchange / licensed redistributor (market-authoritative, licensing friction). **The vendor is
behind an adapter interface (§6.1) so it is replaceable** and so a second vendor can be added for
cross-checking without touching downstream code.

**Trade-off.** EOD-vendor data will *not* exactly equal TV's numbers (different adjustment). We accept
that and manage it as a measured delta (§9) rather than chasing parity — the alternative (enterprise
PIT data) buys parity-grade rigor we don't need for price-derived signals and costs an order of
magnitude more.

### L1 — Ingestion + Data QA

**Decision.** Land vendor data as an **immutable, dated raw dump** (vintage = capture date), then run
a **QA gate** before anything downstream consumes it.

**QA checks (block or quarantine on failure):** calendar gaps vs the exchange trading calendar;
zero/negative prices; **unadjusted-split detection** (extreme single-day return inconsistent with the
CA table); stale/flat prices on suspended names; duplicate (sec_id, date); volume/turnover sanity.

**Why.** EOD vendors ship errors. An unadjusted split silently becomes a fake −80% "signal." Catching
it pre-panel is far cheaper than discovering it as a phantom strategy edge. Immutability + vintage
dating is what makes any historical result reproducible (you can rebuild the exact panel a backtest ran on).

**Alternative considered:** trust-and-go (compute features straight off the vendor feed). Rejected —
one bad CA poisons every downstream statistic and is nearly impossible to trace after the fact.

### L2 — Point-in-time universe & corporate-action reference

**Decision.** A **hand-curated, version-controlled reference dataset** (CSV/YAML in git) that is the
*authoritative* survivorship and eligibility source. Modeled as interval/event rows so membership can
be reconstructed as-of any date:

- **Security master:** `sec_id` (stable internal surrogate), name, `list_date`, `delist_date`,
  `delist_reason` ∈ {merged, acquired, suspended, liquidated, voluntary, …}, `terminal_value`
  (final consideration for return labeling).
- **Time-varying attributes** as intervals: `(sec_id, attribute, value, valid_from, valid_to)` for
  `board` ∈ {main, nomu} and `security_type` ∈ {stock, reit, etf, fund, sukuk} — so "was X a REIT on
  2015-03-01?" is answerable.
- **Corporate actions:** `(sec_id, ca_type, ex_date, ratio_or_amount)`.
- **Ticker map:** `(sec_id, ticker, valid_from, valid_to)` — because 4-digit TADAWUL codes can change
  or be reused. **All joins key on `sec_id`, never the ticker.**

**Why hand-curated.** This is counter-intuitive but correct *for this market*: ~300 names ever makes a
human-auditable PIT table feasible, and it sidesteps the fact that no affordable price vendor reliably
provides PIT classification + delisting reasons + terminal values. It is the **single highest-fidelity
decision available**, and the smallness of TADAWUL is exactly what makes it practical.

**Why eligibility rules must be time-varying, not just the data.** The screen's exclusion logic is
anachronistic if applied unchanged to the past: the Nomu/9xxx parallel market did not exist before
~2017; the REIT category did not exist before ~2016; MSCI-EM inclusion (2019) reshaped liquidity and
composition. The as-of universe filter therefore consults the reference table's *intervals*, and the
*rule set itself* is parameterized by date.

**Trade-off.** Curation is upfront manual effort and must be maintained as new listings/delistings/CAs
occur. Accepted: it is bounded by the market's size, it is auditable, and it removes the largest
hidden bias. **Alternative considered:** derive PIT membership from the price vendor's current
classification. Rejected — it is precisely the survivorship/anachronism bias we are trying to kill.

### L3 — Feature / indicator engine

**Decision.** A **Python 3.12 + Polars** engine that computes the full feature panel from adjusted
OHLCV, implementing the **canonical spec** (§6.4). It is the *only* place indicators are computed for
research. Reuses the exact formulae of the live TS screener:

```
DDmax    = (ATH − low52)/ATH            offLow = close/low52 − 1
belowATH = (ATH − close)/ATH            nrHi   = close/high52
ext60    = close/EMA60 − 1              ema21gap = close/EMA21 − 1
emaComp  = EMA21/EMA60 − 1              vs200  = close/EMA200 − 1
Perf.N   = close/close[t−N] − 1   (null when history < N)
```

**Why Python/Polars, not TypeScript.** The live screener stays TS (it serves the MCP server). But the
research engine wants vectorized columnar compute, a mature quant ecosystem, and lazy multi-symbol
pipelines — Polars over pandas for speed, expressiveness, and lazy execution; numpy underneath. The
cost this creates — *two implementations that can drift* — is neutralized by the executable spec (§6.4)
and CI golden-vector conformance, not by forcing one language.

**Alternative considered:** keep everything in TS to reuse the formula code verbatim (zero drift by
construction). Rejected — it cripples the research/backtest ergonomics (TS has no equivalent of
Polars+vectorbt+DuckDB), and the drift risk it avoids is cheaply covered by golden vectors.

**Trade-off.** We own a second implementation. Mitigation: the spec is executable and both sides run it
in CI; divergence is caught the moment it appears.

### L4 — Panel store

**Decision.** **Parquet** files partitioned by `sec_id` (Hive-style `sec_id=XXXX/…`), queried through
**DuckDB** (embedded, SQL). The materialized panel is the cached, vintage-stamped output of L3.

**Why.** The dataset is ~230 active + delisted names × ~5k bars × ~30 columns ≈ low tens of millions of
cells — trivially small. Columnar Parquet gives cheap, portable, reproducible storage; DuckDB gives
fast analytical SQL with zero operational overhead (no server). Partitioning by `sec_id` makes
per-symbol rebuilds and as-of slices cheap.

**Alternatives considered:** (a) a time-series DB (TimescaleDB/ClickHouse) or warehouse — rejected as
unjustified operational weight at this scale; revisit only if intraday or multi-market arrives. (b)
pandas-in-memory + pickle — rejected for reproducibility and portability. The Parquet+DuckDB choice
scales smoothly to ~100× this size before any rethink is needed.

### L5 — Backtest engine

**Decision.** Two modes, built in this order:

1. **Event-study (first, primary).** For every bar where a screen's entry conditions hold, emit an
   "entry event," then label **forward returns at +20/+60/+120 trading days** (price-return; §6.5).
   Vectorized over the panel: boolean entry mask per (sec_id, date) → shifted-close forward returns.
   This directly answers the only questions we currently have — *does gate X improve forward return,
   out-of-sample?* — and is what `ext60_max`, `p3m_max`, the coil, etc. must be judged by.
2. **Portfolio simulation (later, for tradability).** vectorbt-based: position sizing, the Sun–Thu
   exchange calendar, Saudi commission + spread costs, ADV/`value` capacity limits, → equity curve,
   drawdown, Sharpe. Needed to answer "is the strategy *tradable*," where liquidity actually bites.

**Why build, not adopt a framework.** Off-the-shelf backtesters were considered and rejected: Zipline
(effectively unmaintained, US-calendar-centric), backtrader (event-loop, slow for cross-sectional
sweeps), QuantConnect/LEAN (heavyweight, cloud lock-in). Our needs are a *cross-sectional daily screen*
with full control over the as-of feature semantics and the exact W1/W2/W3 gates — a thin vectorized
layer over the panel is simpler, faster, and auditable. vectorbt is adopted only for the portfolio P&L
mode where reinventing sizing/cost accounting adds no value.

**Trade-off.** We maintain a small engine. Accepted — it is a few hundred lines over a clean panel, and
the control it buys over look-ahead and gate semantics is exactly where fidelity lives.

**Delisting return handling.** Forward-return labeling consults L2: a merged/acquired name realizes its
`terminal_value`; a liquidated/suspended name realizes its recovery/terminal value (often near zero),
**not** its last traded price. Getting this wrong reintroduces bias even with delisted data present.

### L6 — Validation (dual conformance)

This is split deliberately, because the two halves validate *different things* and neither alone is
sufficient.

**L6a — Forward conformance oracle (continuous).** Once per trading day after close, an **automated
headless capture** records TV's live values per eligible symbol — EMA21/60/200, Perf windows, ATH /
52w H/L, DDmax, belowATH, offLow, ext60, nrHi, and the **W1/W2/W3 pass/fail decisions** — each row
stamped with a `capture_ts`. The engine reproduces the same date from the panel; we monitor the
**per-field delta** for *stability* (§9).
- *What it validates:* that the **method**, on **recent** data, tracks TV — and, going forward, that
  code changes don't introduce **drift**.
- *What it cannot validate:* the historical reconstruction of 2006–2025. It only ever sees the present
  onward. This is its structural blind spot.
- *Refinements over the original ledger proposal:* `capture_ts` per row (distinguishes as-captured from
  TV-revised); per-field tolerances; a triage policy (acceptable methodology delta vs bug). **RSI is
  excluded** until a screen actually uses it — we do not validate features we do not trade on.

**L6b — One-time historical reconciliation (build-time).** Because L6a can't vouch for the past — the
exact regime (2006 bubble) that *dominates* `DDmax`/`belowATH` — we additionally, **once**, pull TV's
full history and reconcile the entire panel against (i) TV-history and (ii) a **second EOD vendor**
(cross-vendor agreement), plus spot-checks on known corporate-action dates.
- *What it validates:* the historical substrate and the engine's as-of logic across regimes.

**Why both.** The forward oracle is necessary (drift detection, live alignment) but **not sufficient**
(blind to the past). The historical reconciliation covers the past but is a point-in-time exercise
against a moving TV. Together they bound both axes. Treating the forward ledger as the *sole* oracle —
the tempting simplification — would leave the most important 20 years unvalidated.

### L7 — Research governance (anti-overfitting)

**Decision.** First-class controls, because a fast backtest makes *iteration* the dominant risk:

- **Time-based train/test**, never random (e.g., develop ≤2019, lock-box ≥2020).
- **Walk-forward** rolling out-of-sample evaluation.
- A **rarely-touched holdout** with access logging.
- **Deflated / multiple-testing-aware metrics** — every threshold swept costs a degree of freedom;
  report deflated significance, not the best of N tries.
- **Pre-registration**: a hypothesis and its acceptance criteria are recorded *before* the run.
- **Regime tagging** of all results (2006 crash, 2014 oil, 2019 MSCI inclusion, 2020 COVID).

**Why.** The `ext60_max`-on-n=15 episode is the cautionary tale: a feature read after the move looked
predictive. The platform's job is to make that *structurally* hard to fool yourself with. A gate is
promoted to the live screener only after it survives out-of-sample, deflated, across regimes.

### L8 — Reproducibility & provenance

**Decision.** Every backtest emits a **run manifest** (JSON) pinning: data **vintage** (vendor dump
date), **spec version**, **universe-table version**, **code commit**, parameters, and the holdout
access record. Data is versioned by vintage; the reference table by git history.

**Why.** Without this, results are anecdotes — you cannot tell whether a number changed because the
strategy changed, the data was revised, or a feature definition moved. **Alternative considered:** DVC
or lakeFS for data versioning — deferred; vintage-dated immutable dumps + git suffice at this scale and
add no operational burden.

---

## 5. Tadawul-specific correctness (where naive backtests silently lie)

- **Trading calendar.** TADAWUL trades Sun–Thu, and the weekend *moved* (Thu–Fri → Fri–Sat, ~2013).
  Rolling 252-day windows and `Perf.N` offsets must use an **exchange calendar with Eid holidays**, not
  naïve calendar days. A wrong calendar quietly misaligns every window.
- **Par-value splits.** TADAWUL ran mass par-value splits (SAR 10→1). Unadjusted series make `Perf.*`
  and EMAs garbage across the event; adjusted closes are mandatory, and the panel keeps the unadjusted
  series + `adj_factor` for audit.
- **2006 TASI bubble.** It dominates `ATH` for old names (the absurd insurance-8xxx peaks). The backtest
  must span it; we also expose an optional `ath_lookback_years` so a 2006 peak need not define a 2026
  setup (a strategy choice to be tested, not hard-coded).
- **Currency.** Returns are in SAR (the 3.75 USD peg is moot for return math), but the `value` liquidity
  floor and ADV capacity are SAR turnover. (The live screener converts USD market cap → SAR at 3.75;
  the panel stores SAR-native fields.)
- **Anachronistic eligibility.** Nomu/9xxx (~2017) and REITs (~2016) did not exist early; the as-of
  universe rules must reflect that (§L2).

---

## 6. Data model & contracts

### 6.1 Vendor adapter (interface)

A thin interface `PriceVendor` with `get_eod(sec_id|ticker, start, end) -> bars` and
`get_corporate_actions(...)`, so vendors are swappable and a second vendor can run for cross-checking.

### 6.2 Feature panel (one row per `(sec_id, date)`)

```
sec_id, ticker_asof, date,
open, high, low, close,            # adjusted
unadj_close, adj_factor, volume, value_sar,
ema21, ema60, ema200,
perf_1m, perf_3m, perf_6m, perf_1y, perf_3y, perf_5y, perf_10y,   # null when history < window
ath, high_52w, low_52w,
ddmax, below_ath, off_low, ext60, nrhi, ema21gap, ema_comp, vs200,
in_main_board, is_stock, is_excluded_9xxx, is_reit_etc, age_years, eligible,  # as-of
delist_date, delist_reason, terminal_value          # sparse, for return labeling
spec_version, data_vintage                          # provenance stamps
```

### 6.3 PIT reference tables — see §L2 (security master, attribute intervals, corporate actions, ticker map).

### 6.4 Canonical feature spec (executable)

Not prose alone. The spec is **versioned prose + a language-agnostic golden-vector fixture**: directories
of `input_bars.csv` → `expected_features.csv` with a `spec_version`. **Both** the TS live screener and
the Python engine run the fixtures in CI; a mismatch fails the build. Changing a definition bumps
`spec_version`, which forces a panel rebuild and is recorded in run manifests. When spec and TV disagree,
**spec wins**; the TV delta is documented (§9).

### 6.5 Return semantics (pinned)

The screen's `Perf.*` are **price-return**, so event-study forward returns are **price-return** to
validate gates on like-for-like terms. The portfolio P&L mode additionally maintains a **total-return**
series (dividends reinvested). The two are kept explicitly separate and never blended.

### 6.6 Forward oracle record (one row per `(capture_ts, sec_id)`)

TV-captured features + W1/W2/W3 decisions, per §L6a. This supersedes the ad-hoc `saudi-tracker.jsonl`
role: the journey-tracker remains a *product* view; the oracle is a *validation* artifact. (They may
share a capture but serve different consumers.)

---

## 7. As-of discipline checklist (enforced in L3, audited in L6b)

- `ATH` = running max over `[list_date, t]` — **never** the global series max.
- `high_52w / low_52w` = rolling 252-**trading-day** max/min as-of `t` (exchange calendar).
- EMA warmup respected (EMA200 not emitted until ~200 bars exist).
- `Perf.5Y/10Y = null` when history < window (matches the screens' null handling).
- Universe membership and exclusion rules evaluated **as-of `t`** from the reference intervals.
- `value`/ADV computed from **trailing** windows only.
- No feature at `t` references any bar > `t`.

---

## 8. Technology summary

| Concern | Choice | Why (vs alternative) |
|---|---|---|
| Historical price data | Survivorship-free EOD vendor (adapter-pluggable) | Cheap, sufficient for price-only; enterprise PIT overkill |
| Universe/CA reference | Hand-curated, version-controlled | Highest fidelity; feasible because market is tiny; vendors weak here |
| Feature engine | Python 3.12 + Polars | Best research ergonomics; drift covered by golden vectors |
| Store / query | Parquet (by `sec_id`) + DuckDB | Zero-ops, reproducible, ample at this scale; TSDB unjustified |
| Event-study backtest | Custom vectorized | Full control of as-of + gate semantics; frameworks too rigid |
| Portfolio P&L | vectorbt | Reuse sizing/cost accounting where it adds no edge to rebuild |
| Live screener | TypeScript (unchanged) | Serves the MCP server; bridged to research via golden vectors |
| Orchestration | Make/Python CLI now; Prefect later | Don't pull in Airflow for a small DAG |
| Provenance | Run manifest + vintage-dated dumps | Reproducibility without DVC/lakeFS weight (revisit if it grows) |

---

## 9. Conformance contract (engine ↔ TradingView)

- **Per-field tolerances**, not a single global epsilon (EMA, Perf, ratios differ in sensitivity).
- We monitor the **stability of the delta**, not its absence. Baseline delta is recorded per field; the
  alarm is a *change* in the delta distribution, which implies a bug or a data revision.
- **Triage states** for a breach: `methodology` (known, accepted, documented) · `data-revision` (TV
  restated) · `bug` (engine fault — blocks promotion). A breach is not automatically a defect.
- **Precedence:** canonical spec wins semantic conflicts; TV divergence is a documented, bounded delta.
- Conformance covers **both** the forward oracle (drift) and the one-time historical reconciliation
  (the past).

---

## 10. Repository layout (proposed)

```
research/
  ARCHITECTURE.md                 # this document
  spec/                           # canonical feature spec (prose + golden vectors)
    features.md
    vectors/<feature>/{input_bars.csv,expected.csv}
  reference/                      # hand-curated PIT tables (git-tracked truth)
    security_master.csv
    attribute_intervals.csv
    corporate_actions.csv
    ticker_map.csv
    exchange_calendar.csv
  ingest/                         # vendor adapters + raw immutable dumps (vintage-dated)
  qa/                             # data-quality gate
  engine/                         # Polars feature engine (implements spec/)
  panel/                          # Parquet output + DuckDB views
  backtest/                       # event-study + portfolio sim
  validation/                     # forward oracle capture + historical reconciliation
  governance/                     # experiment tracking, holdout ledger, deflation
  manifests/                      # per-run provenance JSON
```

Deliberately a tracked top-level subsystem, **separate from the gitignored `.claude/`** tooling (the
live screener commands/scripts) and from the TS MCP server `src/`.

---

## 11. Build pipeline (deterministic stages)

```
ingest(vendor, vintage) → qa(vintage) → build_panel(vintage, spec_version)
   → backtest(panel, strategy, params) → manifest(run)
validate_forward(daily)      # independent, scheduled
reconcile_history(once)      # independent, build-time
```

Each stage is a pure function of its pinned inputs; re-running with the same vintage + spec_version +
commit reproduces the result.

---

## 12. Roadmap / phasing (practical today, expandable later)

- **Phase 0 — Foundations.** Vendor selection + delisted-coverage validation; hand-build the PIT
  reference tables; lock the canonical spec + golden vectors; stand up Parquet/DuckDB.
- **Phase 1 — Panel + conformance.** Polars engine to spec; one-time historical reconciliation;
  scheduled forward oracle.
- **Phase 2 — Event-study backtest.** Forward-return labeling; re-run the `ext60_max` question properly
  (out-of-sample, deflated). This is the first real payoff.
- **Phase 3 — Governance + portfolio sim.** Walk-forward, holdout discipline; vectorbt P&L with Saudi
  costs/liquidity.
- **Phase 4 (optional) — Expansion seams** (§13).

---

## 13. Out of scope today — but the seams are left open

- **Fundamentals-based gates** → would extend the PIT discipline to as-reported point-in-time
  fundamentals (a new reference feed); the universe/CA table already models the join.
- **Intraday** → would justify a real TSDB and a different store; the engine/spec split survives.
- **Multi-market** → the adapter + `sec_id` + as-of universe model generalize; calendars become per-market.
- **Live execution** → out of scope; the portfolio sim's cost/capacity model is the on-ramp.

---

## 14. Open decisions to confirm before Phase 0

1. **Primary EOD vendor** — pending a concrete delisted-TADAWUL-through-2006 coverage check.
2. **Second vendor** for cross-vendor reconciliation (L6b) — who, and is the budget there.
3. **`ath_lookback_years`** — cap ATH anchoring (e.g. 10y) so ancient bubble peaks don't define modern
   setups, or keep true all-time? (A strategy question to *test*, not assume.)
4. **Forward-oracle automation** — scheduler choice + headless MCP capture cadence.
5. **Spec ownership** — who is the canonical-spec maintainer / merge authority when spec ↔ TV conflict.

---

*End of v0.1. This is a living document; changes are versioned with the project and should precede the
code they describe.*
