#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Sweeps W1 p6m_min via runtime overrides ONLY; never edits rules.yaml or the live JS.
# Outputs are HYPOTHESES. See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""W1 Perf.6M_min sweep: 60-day rolling replay over the fixed structural cohort, official W1 with ONLY
p6m_min relaxed (0 -> -5/-10/-15/-20). Reports recall vs the official, the newly-detected names, and a
quality proxy (Perf.6M depth, Perf.3M momentum, and return from detection to window end).

    python -m research.experiments.w1_p6m_variants research/panel/tadawul_<vintage>.parquet
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
from research.experiments.w1_variant_replay import diagnose, run_variant  # noqa: E402

EVAL_DAYS = 60
CANDS = [0, -5, -10, -15, -20]   # 0 = official


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    feat = compute_value(compute_age_years(build_panel(prices), sm))
    dates = sorted(feat.get_column("date").unique().to_list())
    eval_dates = dates[-EVAL_DAYS:]
    end = eval_dates[-1]
    W1 = R.load_rules()["W1"]
    uni = feat.filter(
        pl.col("date").is_in(eval_dates) & (~pl.col("sec_id").str.starts_with("9"))
        & (pl.col("age_years") >= 5) & (pl.col("ddmax") >= 50)
        & (pl.col("below_ath") >= 40) & (pl.col("below_ath") <= 100) & (pl.col("off_low") >= 20))
    cohort = sorted(uni.get_column("sec_id").unique().to_list())
    print(f"evaluation: last {EVAL_DAYS} td, {eval_dates[0]}..{end};  fixed structural cohort: {len(cohort)}\n")

    rows = {(r["sec_id"], r["date"]): r for r in R.evaluate_frame(W1, uni, None).iter_rows(named=True)}
    # close on the window-end day from the FULL panel (a name may have left the cohort by then)
    end_close = {r["sec_id"]: r["close"] for r in feat.filter(pl.col("date") == end).iter_rows(named=True)}

    results, official_det = {}, None
    for c in CANDS:
        ov = {} if c == 0 else {"p6m_min": c}
        rws, ff = run_variant(uni, W1, ov)
        det = {s for s in cohort if s in ff}
        if c == 0:
            official_det = det
        miss_block = Counter()
        for s in cohort - det if isinstance(cohort, set) else (s for s in cohort if s not in det):
            srows = sorted([rws[(s, d)] for d in eval_dates if (s, d) in rws], key=lambda r: r["date"])
            bl = Counter()
            for r in srows:
                for g in diagnose(W1, r, ov):
                    bl[g] += 1
            if bl:
                miss_block[bl.most_common(1)[0][0]] += 1
        results[c] = (det, ff, miss_block)

    print(f"{'p6m_min':>8}{'detected':>10}{'missed':>8}{'new':>5}{'lost':>5}   dominant blocking gates among missed")
    for c in CANDS:
        det, ff, mb = results[c]
        new = det - official_det
        lost = official_det - det
        tag = " (official)" if c == 0 else ""
        print(f"{c:>8}{len(det):>10}{len(cohort)-len(det):>8}{len(new):>5}{len(lost):>5}   "
              + ", ".join(f"{k} {v}" for k, v in mb.most_common(4)) + tag)

    # newly-detected detail with quality proxy, attributed to the threshold that first admits them
    print("\nNEWLY-detected names (vs official), with quality proxy "
          "[Perf.6M @entry, Perf.3M @entry, belowATH, ret detection→end, days held]:")
    print(f"  {'added@':>7} {'sym':6}{'P6M':>5}{'P3M':>5}{'bATH':>5}{'offLo':>6}{'firstPass':>12}{'ret→end':>8}{'held':>5}")
    seen = set()
    for c in CANDS[1:]:
        det, ff, _ = results[c]
        for s in sorted(det - official_det):
            if s in seen:
                continue
            seen.add(s)
            d = ff[s]
            r = rows[(s, d)]
            ec = end_close.get(s)
            ret = (ec / r["close"] - 1) * 100 if (ec and r["close"]) else None
            held = sum(1 for dd in eval_dates if dd >= d)
            p6 = f"{r['perf_6m']:.0f}" if r['perf_6m'] is not None else "—"
            rr = f"{ret:+.0f}" if ret is not None else "—"
            print(f"  {c:>7} {s:6}{p6:>5}{r['perf_3m']:>5.0f}{r['below_ath']:>5.0f}{r['off_low']:>6.0f}"
                  f"{str(d):>12}{rr:>8}{held:>5}")

    print("\n(Experimental — hypotheses only. Official W1 unchanged. ret→end is a within-window quality "
          "proxy; names detected near the end have few days held.)")


if __name__ == "__main__":
    main()
