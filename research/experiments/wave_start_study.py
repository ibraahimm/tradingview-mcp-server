#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Uses runtime params_overrides and/or observable candidate pre-filters; it never edits
# rules.yaml or the live JS. Outputs are HYPOTHESES, not the documented methodology.
# See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""Case study: why do strongly-launching names (Perf.1M>10% & offLow>20%) get missed by TASI-W1 and TASI-W2?

    python -m research.wave_start_study research/panel/tadawul_<vintage>.parquet [asof_back_td]

Goal context (user): catch names where a LONG, DEEP multi-year correction has ended and a NEW cycle
has just started. The complaint: 40+ names are up >10% (most >30%) on the month and well off their low,
yet neither TASI-W1 nor TASI-W2 picks them. This prints the candidate set and the EXACT first-failing gate per
name for both screens, so we can see which conditions block the new-cycle launches.
"""
from __future__ import annotations
import os
import sys
from collections import Counter
from statistics import median

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load                                   # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402
from research.backtest.rigor import with_td_idx                      # noqa: E402


def hist(decided, label):
    n = decided.height
    npass = decided.filter(pl.col("passed")).height
    fails = Counter(decided.filter(~pl.col("passed")).get_column("first_fail").to_list())
    print(f"\n{label}: {npass}/{n} pass.  First-failing gate (why the rest are rejected):")
    for gate, c in fails.most_common():
        print(f"    {gate:14} {c:3}  ({100*c/n:.0f}%)")


def main():
    prices = load(sys.argv[1])
    back = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    feat = with_td_idx(compute_value(compute_age_years(build_panel(prices), sm)))
    dates = sorted(feat.get_column("date").unique().to_list())
    asof = dates[-1 - back]
    snap = feat.filter(pl.col("date") == asof)
    print(f"as-of {asof}  ({snap.height} names trading that day)")

    cand = snap.filter((pl.col("perf_1m") > 10) & (pl.col("off_low") > 20))
    p1m = cand.get_column("perf_1m").to_list()
    print(f"\nCANDIDATES (Perf.1M>10% AND offLow>20%): {cand.height}")
    print(f"  Perf.1M: median {median(p1m):.0f}%, >30%: {sum(x>30 for x in p1m)}, max {max(p1m):.0f}%")
    print(f"  offLow : median {median(cand.get_column('off_low').to_list()):.0f}%")
    deep = cand.filter((pl.col("ddmax") >= 50) | (pl.col("below_ath") >= 40)).height
    print(f"  deeply-corrected DNA (DDmax>=50 OR belowATH>=40): {deep}/{cand.height}")

    rules = R.load_rules()
    hist(R.evaluate_frame(rules["TASI-W1"], cand, None), "TASI-W1 (/tasi-w1)")
    hist(R.evaluate_frame(rules["TASI-W2"], cand, None), "TASI-W2 (/tasi-w2)")

    # which candidates pass NEITHER, and the headline blocking values
    dW1 = R.evaluate_frame(rules["TASI-W1"], cand, None)
    dW2 = R.evaluate_frame(rules["TASI-W2"], cand, None)
    miss = dW1.filter(~pl.col("passed")).join(dW2.filter(~pl.col("passed")).select("sec_id"), on="sec_id")
    print(f"\nMissed by BOTH TASI-W1 and TASI-W2: {miss.height}/{cand.height}")
    print(f"  {'sym':6}{'p1m':>6}{'p3m':>6}{'p6m':>6}{'offLo':>6}{'DDmx':>6}{'bATH':>6}{'TASI-W1 fail':>10}{'TASI-W2 fail':>10}")
    show = dW1.join(dW2.select(["sec_id", pl.col("first_fail").alias("w2_fail"), pl.col("passed").alias("w2_pass")]),
                    on="sec_id").sort("perf_1m", descending=True)
    for r in show.iter_rows(named=True):
        if r["passed"] or r["w2_pass"]:
            continue
        print(f"  {r['sec_id']:6}{r['perf_1m']:>6.0f}{r['perf_3m']:>6.0f}{r['perf_6m']:>6.0f}"
              f"{r['off_low']:>6.0f}{r['ddmax']:>6.0f}{r['below_ath']:>6.0f}{str(r['first_fail']):>10}{str(r['w2_fail']):>10}")


if __name__ == "__main__":
    main()
