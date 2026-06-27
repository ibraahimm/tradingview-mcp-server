# Conformance Contract — Research Engine ↔ Live TradingView Screener

Defines how we keep the Python research engine and the live TV screener **aligned without forcing
them identical**. Per the three-truths model (`../ARCHITECTURE.md` §2): the **canonical spec wins**
all semantic conflicts; TV is the execution reference whose delta we **monitor for stability**, not
drive to zero. Matching TV exactly would chase a moving target and import its quirks into the backtest.

## Two conformance modes (both required)

| Mode | When | Validates | Cannot validate |
|---|---|---|---|
| **Forward oracle** (`schema/oracle_record.schema.json`) | every trading day, after close | the method on recent data + ongoing **drift** | the historical reconstruction (it only sees present→future) |
| **Historical reconciliation** | once at build, re-run on spec/data change | the as-of engine across regimes (incl. 2006) | live drift (it's a point-in-time exercise) |

The forward oracle is **necessary but not sufficient** — it is structurally blind to 2006–2025, the
regime that dominates `DDmax`/`belowATH`. The historical reconciliation covers that gap by comparing
the full reconstructed panel against (i) a one-time TV-history pull and (ii) a **second data vendor**
(cross-vendor agreement), with spot-checks on known corporate-action dates.

## Per-field tolerance (a value "matches" within these)

| Field group | abs (pp) | rel | Expected source of delta |
|---|---|---|---|
| `ema21/60/200` | 0.02 | 1e-3 | seed/warmup convention (washes out with history) |
| `perf_1m … perf_10y` | 0.10 | 1e-3 | calendar/holiday edge of the as-of-or-before anchor |
| `ddmax, below_ath, off_low, nrhi` | 0.25 | 2e-3 | intraday vs close extremes for ATH/52w |
| `ext60, ema21gap, ema_comp, vs200` | 0.10 | 1e-3 | inherited from EMA |
| `w1_pass, w2_pass, w3_pass` | exact boolean | — | must agree, **except** borderline (below) |

"Matches" = `abs(got-exp) <= abs` **or** `abs(got-exp) <= rel*abs(exp)`. Tolerances are *ceilings on the
expected methodology delta*, not targets — see monitoring.

- **EMA warmup exemption:** names with `bar_count < 3×length` are reported *informational-only* for that
  EMA (seed still material); they do not count toward pass/fail.
- **Rule borderline rule:** a `w*_pass` disagreement is **not** a failure when any gating feature sits
  within its tolerance band of a threshold (the decision is legitimately knife-edge). It is logged as
  `borderline` and excluded from the agreement rate.

## Monitoring: stability, not absence

We do not alarm on the *presence* of a delta — a stable +0.3% EMA gap from a seeding convention is fine
forever. We baseline each field's delta distribution (median + IQR over a trailing window) and **alarm
on a change**: median shift beyond `k·IQR`, a jump in out-of-tolerance rate, or new persistent outliers.
A *change* implies one of the triage classes below.

## Triage states (every breach is classified)

| Class | Meaning | Action |
|---|---|---|
| `methodology` | stable, explained delta (seed, calendar, adjustment) | record in the delta registry; **accept** |
| `data-revision` | TV restated a past value vs a prior capture | annotate; not an engine fault |
| `bug` | engine fault | **blocks promotion**; fix, add a golden vector, re-run |

A breach is **not** automatically a defect. The default disposition for a new, small, stable delta is
`methodology` pending review — but an *unexplained* or *growing* delta escalates to `bug`.

## Promotion gate (when a new rule/threshold may go live)

A change to a screen rule or threshold may be promoted into the live TS screener only if **all** hold:
1. Golden vectors pass for the engine (`../spec/conformance`).
2. Forward-oracle **rule-decision agreement ≥ 99%** over the trailing N≥20 trading days, excluding
   `borderline`.
3. No open `bug`-class conformance breach on any input feature of that rule.
4. Out-of-sample backtest evidence exists (research governance, `../ARCHITECTURE.md` §L7) — conformance
   proves *fidelity*, not *edge*.

## Precedence (restated, because it is the crux)

When canonical spec and TV disagree: **spec wins.** The TV divergence is recorded as a bounded,
documented delta — never resolved by editing a spec definition to match TV. The delta registry is the
audit trail of every accepted `methodology` difference and its explanation.
