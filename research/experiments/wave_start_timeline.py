#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Uses only OBSERVABLE candidate pre-filters; the W1 pass/fail decision comes solely from
# evaluate_frame on the official rule (no params_overrides). It never edits rules.yaml or the live JS.
# Outputs are HYPOTHESES, not the documented methodology. See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""W1 wave-start timeline (faithful): for deep-correction names now launching that the OFFICIAL W1 misses,
trace the daily gate sequence to see whether the launch skipped W1's measured window.

    python -m research.experiments.wave_start_timeline research/panel/tadawul_<vintage>.parquet

Candidate set = OBSERVABLE launch criteria only: non-9xxx (Nomu/parallel — not targets, per the docs),
Perf.1M>10, offLow>20, DDmax>=50 (the deep-correction criterion). NO perf_3y<=0 filter (that was a prior
error: perf_3y<=0 is the W1 ★ TAG, not a gate; the actual W1 gate is perf_3y<50). Misses are decided by
W1's ACTUAL gates via evaluate_frame with NO overrides, so this uses the official below_max=100 now in
rules.yaml. For each miss we trace when each gate threshold is first crossed.
"""
from __future__ import annotations
import os
import sys
from collections import Counter

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load                                   # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402
from research.backtest.rigor import with_td_idx                      # noqa: E402

WIN = 180


def first_day(rows, pred):
    for r in rows:
        if pred(r):
            return r
    return None


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    feat = with_td_idx(compute_value(compute_age_years(build_panel(prices), sm)))
    end = feat.get_column("date").max()
    snap = feat.filter(pl.col("date") == end)
    W1 = R.load_rules()["W1"]   # OFFICIAL rule, no overrides

    # OBSERVABLE candidate pre-filters only (non-9xxx, launching, deeply corrected)
    cand = snap.filter((~pl.col("sec_id").str.starts_with("9")) & (pl.col("perf_1m") > 10) &
                       (pl.col("off_low") > 20) & (pl.col("ddmax") >= 50))
    decided = R.evaluate_frame(W1, cand, None)          # official gates, no overrides
    npass = decided.filter(pl.col("passed")).height
    miss = decided.filter(~pl.col("passed"))
    print(f"as-of {end}: deep-correction launchers (non-9xxx, P1M>10, offLow>20, DDmax>=50): {cand.height}")
    print(f"  official W1 PASSES {npass}, MISSES {miss.height}\n")
    print("why the misses are rejected (W1 first-failing gate):")
    for g, c in Counter(miss.get_column("first_fail").to_list()).most_common():
        print(f"    {g:12} {c}")

    print(f"\n{'sym':6}{'P1M':>5}{'P3M':>5}{'P6M':>5}{'offLo':>6}{'bATH':>5}{'W1fail':>9}   timeline of first crossings")
    for r0 in miss.sort("perf_1m", descending=True).iter_rows(named=True):
        sid = r0["sec_id"]
        rows = list(feat.filter((pl.col("sec_id") == sid) & (pl.col("td_idx") >= r0["td_idx"] - WIN))
                    .sort("td_idx").iter_rows(named=True))
        d_off60 = first_day(rows, lambda r: r["off_low"] is not None and r["off_low"] >= 60)
        d_p3m40 = first_day(rows, lambda r: r["perf_3m"] is not None and r["perf_3m"] >= 40)
        d_p6m0 = first_day(rows, lambda r: r["perf_6m"] is not None and r["perf_6m"] > 0)
        w1days = sum(1 for r in rows if R.evaluate(W1, r, None)[0])

        def dd(x):
            return str(x["date"]) if x else "—never—"
        print(f"{sid:6}{r0['perf_1m']:>5.0f}{r0['perf_3m']:>5.0f}{r0['perf_6m']:>5.0f}"
              f"{r0['off_low']:>6.0f}{r0['below_ath']:>5.0f}{str(r0['first_fail']):>9}   "
              f"P6M>0:{dd(d_p6m0)}  offLo≥60:{dd(d_off60)}  P3M≥40:{dd(d_p3m40)}  W1-window:{w1days}d")

    print("\n(Experimental — hypotheses only. Official W1 = rules.yaml + saudi-stage2.js.)")


if __name__ == "__main__":
    main()
