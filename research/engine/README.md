# Research Feature Engine — `research/engine/`

The **Polars** implementation of the canonical feature spec (`../spec/features.yaml`). It is the
research-side half of the two-implementation design (the live TS screener is the other); the
**golden vectors** (`../spec/vectors`) are the shared acceptance gate that keeps the two identical.

## Scope (deliberately minimal — W1 / stage2 first)

| Implemented now | Status |
|---|---|
| `ema` (spec function) | ✅ Polars `ewm_mean(adjust=False)` + explicit warmup nulling |
| `perf_calendar` (spec function) | ✅ Polars backward `join_asof` (as-of-or-before, calendar-anchored) |
| `ratios` (8 structural features) | ✅ single-source `RATIO_EXPRS` Polars expressions; null-propagating |

All three pass the existing golden vectors against the **real engine**:

```
python research/spec/conformance/reference_runner.py --adapter=research.engine.conformance:FUNCTIONS
# -> PASS: 3 case(s), spec_version 1.0.0, coverage OK.
```

## Explicitly deferred (do NOT add ahead of the spec)

- **Window anchors** `ath` / `high_52w` / `low_52w` (`running_max`, `rolling_extreme`). W1 needs them
  to *feed* the ratios, but they currently have `vectors: []` in the spec. **Discipline: add their
  golden vectors first, then implement** — they must not enter the engine ungated.
- **Panel assembly** — binding `features.yaml` (ema21/60/200, perf_1m…10y, the ratios) over a real
  price frame into the `(sec_id, date)` panel. This is the next increment, and it consumes the window
  anchors above. `RATIO_EXPRS` is written to vectorize directly at that point (same dict, applied to
  the whole frame instead of a 1-row frame).
- **Rule evaluation** (`../spec/rules.yaml`) and the backtest — later layers.

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
