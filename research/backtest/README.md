# Event-Study Backtest — `research/backtest/`

The layer that finally answers gate questions (e.g. `ext60_max`) **out-of-sample**: label every
bar's signal with its forward return, then aggregate. It runs on the decided/labeled panel the
screen run produces — no market data needed for the gate (the self-test uses a controlled panel).

## Forward-return definition (the spec decision this layer pins)

For a signal at `(sec_id, date_t)` with close `c_t` and horizon `H` trading days:

```
if a bar exists H trading days ahead (same sec_id):   fwd = (close[t+H] / c_t - 1) * 100   # price-return
elif the security is DELISTED (delist_date & terminal_value known):
                                                       fwd = (terminal_value / c_t - 1) * 100
else (right-censored: data ends, still listed):        fwd = null   # outcome unknown -> excluded
```

- **Price-return** (not total-return), to match the screen's `Perf.*` semantics — like-for-like with
  the gates being evaluated.
- **Delisting terminal value** (from the reference `security_master`) is realized when the horizon
  extends past a delisted security's last bar — so a bankruptcy/merger resolves at its recovery value,
  **not** its last traded price. Getting this wrong is the classic survivorship-adjacent bias.
- **Right-censoring**: a still-listed security whose data simply hasn't reached `t+H` yet gets `null`
  and is excluded from aggregates (no peeking, no fabricated outcome).
- **Trading-day horizon**: `H` is a bar count (the panel is one row per trading day), so the horizon
  uses the exchange calendar implicitly.

## API

- `label_forward_returns(panel, security_master, horizons=(20,60,120))` → panel + `fwd_<H>` columns.
- `aggregate(labeled, horizon, mask=None)` → `{n, hit_rate, mean, median}` over non-null `fwd_H`.
- `event_study(labeled, horizon, signal_col="passed")` → `{signals, rest}` aggregates — the A/B that
  shows whether the screen's survivors out-perform the rest at that horizon.

## Gate

`selftest_event_study.py` (CI) asserts the labels by hand on a controlled panel — normal forward
returns, the delisting terminal-value tail, right-censored nulls — plus the aggregates and the
signals-vs-rest split.

## Deferred

Portfolio simulation (sizing, costs, ADV capacity, equity curve) and the research-governance
controls (walk-forward, holdout, deflated metrics) build on this core; they are later increments.
