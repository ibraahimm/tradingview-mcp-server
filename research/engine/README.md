# Research Feature Engine — `research/engine/`

The **Polars** implementation of the canonical feature spec (`../spec/features.yaml`). It is the
research-side half of the two-implementation design (the live TS screener is the other); the
**golden vectors** (`../spec/vectors`) are the shared acceptance gate that keeps the two identical.

## Scope (W1 / stage2 feature set)

| Implemented | Status |
|---|---|
| `ema` (spec function) | ✅ Polars `ewm_mean(adjust=False)` + explicit warmup nulling |
| `perf_calendar` (spec function) | ✅ Polars backward `join_asof` (as-of-or-before, calendar-anchored) |
| `running_max` → `ath` | ✅ Polars `cum_max`; trailing `lookback_years` via time-rolling |
| `rolling_extreme` → `high_52w`/`low_52w` | ✅ Polars time-rolling over `[date-weeks·7d, date]` |
| `ratios` (8 structural features) | ✅ single-source `RATIO_EXPRS`; null-propagating |
| **panel builder** (`panel.py`) | ✅ `(sec_id, date)` panel; per-security, as-of, reuses the gated functions |
| **rule engine** (`rules.py`) | ✅ W1/W2/W3 pass/fail + first-failing-gate + funnel, driven by `../spec/rules.yaml` |
| **screen run** (`screen.py`) | ✅ joins `age_years` (reference) + `value`/ADV (liquidity), then funnel + survivors over the panel |

Acceptance gates (all green; wired into CI):

```
# golden vectors against the REAL engine
python research/spec/conformance/reference_runner.py --adapter=research.engine.conformance:FUNCTIONS
# -> PASS: 7 case(s), spec_version 1.0.0, coverage OK.

# panel builder: isolation / warmup / null-propagation / consistency
python -m research.engine.selftest_panel
# -> PASS: panel self-test OK

# rule engine: W1/W2/W3 decisions + funnel order (row-wise == frame-wise)
python research/spec/conformance/rule_runner.py
# -> PASS: 4 rule case(s) across ['W1', 'W2', 'W3'], coverage OK.

# screen run: age_years + value/ADV enrichment, funnel + survivors (2 runs)
python -m research.engine.selftest_screen
# -> PASS: screen-run self-test OK
```

The panel builder reuses the **same** golden-vector-gated functions per security, so every column is
correct by construction; `RATIO_EXPRS` is applied once over the whole frame (same dict the 1-row
conformance adapter uses). Per-security `group_by` enforces as-of isolation structurally — no value
references another security or a future bar (the self-test asserts no cross-sec leakage).

## Explicitly deferred (do NOT add ahead of the spec)

- **Event-study backtest core** is now implemented in `../backtest/` (forward-return labeling with
  delisting terminal values + censoring, aggregates, signals-vs-rest A/B) — the layer that answers the
  `ext60_max` question out-of-sample. It consumes the screen run's per-bar signals.
- **Portfolio simulation** (sizing, costs, ADV capacity, equity curve) and **research governance**
  (walk-forward, holdout, deflated metrics) build on that core — later increments.
- Anything requiring real market data (ingestion, the production reference table, vendor wiring) — the
  panel builder consumes an *adjusted OHLCV frame*; producing that frame is the data layer, out of scope here.

This staging is intentional: minimal, fully gated, expanded only as the canonical spec grows.

## Design notes

- **Boundary I/O matches the adapter contract** (lists / row-dicts), so the runner is implementation-
  agnostic. Polars is used *internally*; the same `ratios` definition (`RATIO_EXPRS`) is reused
  verbatim when the panel builder arrives — one definition, two call sites.
- **Spec wins.** Polars' `ewm_mean(adjust=False)` happens to match the spec's first-value seed; the
  warmup window is nulled explicitly rather than relying on `min_periods`, so the semantics are ours,
  not the library's. Any residual difference vs TradingView is a *monitored delta*
  (`../validation/CONFORMANCE.md`), never reconciled by editing a definition.
- **Null propagation is automatic** in `ratios`: any null input yields a null output (e.g. `ext60` is
  null while `ema60` is in warmup), matching the spec's null policy without special-casing.

## Dependencies

`polars` only (`pip install polars`). Python ≥ 3.9.
