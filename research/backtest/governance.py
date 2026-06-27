"""Research governance: out-of-sample-by-default evaluation primitives.

Exists to prevent the exact failure that motivated this platform — a gate that looked predictive
in-sample (the `ext60_max` n=15 hindsight trap). These make time-ordered train/test, walk-forward,
and multiple-testing deflation the default way any gate is judged. See ARCHITECTURE.md §L7.

Discipline encoded here:
  - splits are by DATE, never random (no future leaking into the past);
  - gate SELECTION scores on TRAIN and reports the held-out TEST result (never selects on test);
  - a winner chosen as best-of-K configs has its p-value DEFLATED by K (multiple testing).
"""
from __future__ import annotations
import math
import statistics
from statistics import NormalDist

import polars as pl


def time_split(labeled: pl.DataFrame, cutoff_date):
    """Time-ordered split (never random): (train = date <= cutoff, test = date > cutoff)."""
    return (labeled.filter(pl.col("date") <= cutoff_date),
            labeled.filter(pl.col("date") > cutoff_date))


def _vals(df: pl.DataFrame, horizon: int, signal_col: str | None):
    d = df.filter(pl.col(signal_col)) if signal_col else df
    return [v for v in d.get_column(f"fwd_{horizon}").to_list() if v is not None]


def summary_stats(values) -> dict:
    """{n, mean, std, t, p} for a forward-return sample vs 0. `p` is a two-sided NORMAL (z)
    approximation — adequate for n>=~30; for rigorous small-n inference use a t-distribution."""
    n = len(values)
    if n < 2:
        return {"n": n, "mean": (values[0] if n else None), "std": None, "t": None, "p": None}
    m = statistics.fmean(values)
    s = statistics.stdev(values)
    if s == 0:
        return {"n": n, "mean": m, "std": 0.0, "t": None, "p": None}
    t = m / (s / math.sqrt(n))
    p = 2 * (1 - NormalDist().cdf(abs(t)))
    return {"n": n, "mean": m, "std": s, "t": t, "p": p}


def bonferroni(p, n_trials) -> float | None:
    """Multiple-testing deflation: a p-value earned as best-of-`n_trials` is inflated; the
    Bonferroni-deflated value is min(1, p * n_trials)."""
    if p is None:
        return None
    return min(1.0, p * max(1, int(n_trials)))


def walk_forward(labeled: pl.DataFrame, horizon: int, cutoffs, signal_col: str = "passed") -> list:
    """Bucket a FIXED gate's out-of-sample results by time window. Sorted cutoffs c1<...<cm define
    windows (c_{k-1}, c_k] (c_0 = -inf); returns one summary per window. Nothing in-sample is ever
    surfaced. (Gate SELECTION across configs uses select_best_oos.)"""
    folds = []
    prev = None
    for c in sorted(cutoffs):
        win = (labeled.filter(pl.col("date") <= c) if prev is None
               else labeled.filter((pl.col("date") > prev) & (pl.col("date") <= c)))
        folds.append({"test_end": c, "stats": summary_stats(_vals(win, horizon, signal_col))})
        prev = c
    return folds


def select_best_oos(named_train_test: dict, horizon: int, signal_col: str = "passed") -> dict:
    """Anti-curve-fit selection. `named_train_test` = {config: (train_df, test_df)}.
    Selects the config with the best **TRAIN** mean, then reports that config's held-out **TEST**
    stats, with the test p-value deflated by the number of configs tried. Returns
    {best, n_trials, train, test, deflated_p, all_train}."""
    n_trials = len(named_train_test)
    train_stats = {name: summary_stats(_vals(tr, horizon, signal_col))
                   for name, (tr, _te) in named_train_test.items()}
    best = max(train_stats, key=lambda k: (train_stats[k]["mean"]
                                           if train_stats[k]["mean"] is not None else -math.inf))
    test_stats = summary_stats(_vals(named_train_test[best][1], horizon, signal_col))
    return {
        "best": best,
        "n_trials": n_trials,
        "train": train_stats[best],
        "test": test_stats,
        "deflated_p": bonferroni(test_stats["p"], n_trials),
        "all_train": train_stats,
    }
