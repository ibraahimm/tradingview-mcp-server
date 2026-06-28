"""Analysis-rigor layer — turns "signals vs all bars" into a defensible, OOS, deflated answer.

Three fixes over the indicative event-study:
  1. dedup_signals  — non-overlapping signals (one per name per holding window) so the sample is
     INDEPENDENT, not 35k autocorrelated daily repeats of the same setup.
  2. add_excess     — date-matched MARKET-NEUTRAL excess return (signal minus the cross-sectional
     mean that day), removing the regime/time confound in comparing to "the rest".
  3. (composed with backtest.governance) time-split, walk-forward, Bonferroni deflation.

Used by research/rigor_run.py. Gated by selftest_rigor.py.
"""
from __future__ import annotations

import polars as pl

from .governance import summary_stats


def add_excess(labeled: pl.DataFrame, horizons) -> pl.DataFrame:
    """Add `xs_<h>` = fwd_<h> minus the cross-sectional mean of fwd_<h> on that date (market-neutral)."""
    out = labeled
    for h in horizons:
        out = out.with_columns(
            (pl.col(f"fwd_{h}") - pl.col(f"fwd_{h}").mean().over("date")).alias(f"xs_{h}")
        )
    return out


def with_td_idx(df: pl.DataFrame) -> pl.DataFrame:
    """Trading-day index within each security (0-based), so dedup spacing is in trading days."""
    return df.sort(["sec_id", "date"]).with_columns(td_idx=pl.int_range(pl.len()).over("sec_id"))


def dedup_signals(decided: pl.DataFrame, horizon: int, signal_col: str = "passed") -> pl.DataFrame:
    """Greedy non-overlapping selection per security: keep a signal only if at least `horizon`
    trading-day bars have passed since the last kept signal for that name. Requires `td_idx`."""
    sig = decided.filter(pl.col(signal_col)).sort(["sec_id", "td_idx"])
    last: dict = {}
    mask = []
    for r in sig.iter_rows(named=True):
        s, idx = r["sec_id"], r["td_idx"]
        if s not in last or idx - last[s] >= horizon:
            mask.append(True)
            last[s] = idx
        else:
            mask.append(False)
    return sig.filter(pl.Series("keep", mask)) if mask else sig


def study(decided: pl.DataFrame, horizon: int, signal_col: str = "passed", excess: bool = True) -> dict:
    """Dedup the signals, then summarize their (market-neutral, by default) forward return:
    {n, mean, std, t, p, raw_signals, independent}. `n`==`independent` is the honest sample size."""
    kept = dedup_signals(decided, horizon, signal_col)
    col = f"xs_{horizon}" if excess else f"fwd_{horizon}"
    vals = [v for v in kept.get_column(col).to_list() if v is not None]
    st = summary_stats(vals)
    st["raw_signals"] = decided.filter(pl.col(signal_col)).height
    st["independent"] = len(vals)
    return st
