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

## Governance (`governance.py`) — out-of-sample by default

The discipline that makes an aggregate *trustworthy* rather than another `ext60_max` hindsight trap:

- `time_split(labeled, cutoff)` → train/test **by date** (never random).
- `summary_stats(values)` → `{n, mean, std, t, p}` (two-sided z-approx) for a forward-return sample.
- `bonferroni(p, n_trials)` → deflate a best-of-K p-value (multiple testing).
- `walk_forward(labeled, horizon, cutoffs)` → a fixed gate's **per-window** OOS aggregates.
- `select_best_oos({config: (train, test)}, horizon)` → selects on **TRAIN**, reports the held-out
  **TEST**, deflated by the number of configs. It will **not** pick the config that only looks good
  on test — that is the whole point.

## Gates (CI)

- `selftest_event_study.py` — labels by hand (normal / terminal-value tail / censored null), aggregates, A/B.
- `selftest_governance.py` — time split, stats, Bonferroni, walk-forward, and the select-on-train /
  report-on-test / deflate discipline.

## Deferred

Portfolio simulation (sizing, costs, ADV capacity, equity curve) builds on this core; it is a later
increment, and it is about *tradability* — which only matters once a gate has survived governance.
