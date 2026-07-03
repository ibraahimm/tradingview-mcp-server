#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Compares OFFICIAL TASI-W1 against parameter VARIANTS using runtime overrides ONLY (params_overrides).
# Never edits rules.yaml or the live JS. Outputs are HYPOTHESES. See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""TASI-W1 variant 60-day rolling replay: compare official TASI-W1 vs Variant A (later offLow entry zone) over the
SAME fixed structural cohort, with the same audit outputs as w1_replay_60d.

    python -m research.experiments.w1_variant_replay research/panel/tadawul_<vintage>.parquet

Structural cohort_d (fixed; the intended TASI-W1 universe) = non-9xxx & age>=5 & DDmax>=50 &
    belowATH in [40,100] & offLow>=20.  Only the TASI-W1 OFFLOW gate is changed, via override.

Variant A override: {offlow_min:40, offlow_max:80}.  (Variant B is run only if A's evidence warrants it.)
"""
from __future__ import annotations
import csv
import os
import sys
from collections import Counter

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load                                   # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402

EVAL_DAYS = 60
OUT = ".claude/outputs"
VARIANTS = [("official", {}), ("A", {"offlow_min": 40, "offlow_max": 80})]


def _pname(raw):
    return raw[1:] if isinstance(raw, str) and raw.startswith("@") else None


def diagnose(rule, row, ov):
    """All failing TASI-W1 gates under params + override; returns the dominant param to change."""
    params = {**rule["params"], **ov}
    fails = []
    for pred in rule["funnel"]:
        if not R._enabled(pred, params):
            continue
        feat, op, raw = pred["feature"], pred["op"], pred["value"]
        x = row.get(feat)
        if x is None:
            if pred.get("null_action") == "drop":
                fails.append(feat)
            continue
        if op in ("ge", "gt", "le", "lt"):
            if not R._OPS[op](x, R._resolve(raw, params)):
                fails.append(_pname(raw) or feat)
        else:
            lo_r, hi_r = raw
            lo, hi = R._resolve(lo_r, params), R._resolve(hi_r, params)
            if not R._OPS[op](x, [lo, hi]):
                lo_incl = op in ("in_co", "in_cc")
                fails.append((_pname(lo_r) if ((x < lo) if lo_incl else (x <= lo)) else _pname(hi_r)) or feat)
    return fails


def run_variant(uni, TASI_W1, ov):
    dec = R.evaluate_frame(TASI_W1, uni, ov)
    rows = {(r["sec_id"], r["date"]): r for r in dec.iter_rows(named=True)}
    first_fire = {}
    for (sid, d), r in rows.items():
        if r["passed"] and (sid not in first_fire or d < first_fire[sid]):
            first_fire[sid] = d
    return rows, first_fire


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    feat = compute_value(compute_age_years(build_panel(prices), sm))
    dates = sorted(feat.get_column("date").unique().to_list())
    eval_dates = dates[-EVAL_DAYS:]
    TASI_W1 = R.load_rules()["TASI-W1"]
    uni = feat.filter(
        pl.col("date").is_in(eval_dates) & (~pl.col("sec_id").str.starts_with("9"))
        & (pl.col("age_years") >= 5) & (pl.col("ddmax") >= 50)
        & (pl.col("below_ath") >= 40) & (pl.col("below_ath") <= 100) & (pl.col("off_low") >= 20))
    cohort = sorted(uni.get_column("sec_id").unique().to_list())
    print(f"evaluation: last {EVAL_DAYS} td, {eval_dates[0]}..{eval_dates[-1]}")
    print(f"fixed structural cohort: {len(cohort)} symbols\n")

    per = {}   # variant -> {sid: (detected, first_pass, dominant_block)}
    for name, ov in VARIANTS:
        rows, ff = run_variant(uni, TASI_W1, ov)
        res = {}
        miss_block = Counter()
        for sid in cohort:
            srows = sorted([rows[(sid, d)] for d in eval_dates if (sid, d) in rows], key=lambda r: r["date"])
            fp = ff.get(sid)
            det = bool(fp)
            if not det:
                bl = Counter()
                for r in srows:
                    for g in diagnose(TASI_W1, r, ov):
                        bl[g] += 1
                dom = bl.most_common(1)[0][0] if bl else "—"
                miss_block[dom] += 1
            else:
                dom = "(detected)"
            res[sid] = (det, fp, dom)
        per[name] = res
        ndet = sum(1 for s in cohort if res[s][0])
        print(f"[{name}] override={ov or 'none'}")
        print(f"    detected {ndet}/{len(cohort)}   missed {len(cohort)-ndet}")
        print(f"    dominant blocking gate among missed: " +
              ", ".join(f"{k} {v}" for k, v in miss_block.most_common()))

    # symbol-level diff vs official
    off, A = per["official"], per["A"]
    newly = [s for s in cohort if A[s][0] and not off[s][0]]
    lost = [s for s in cohort if off[s][0] and not A[s][0]]
    print(f"\nVariant A vs official — symbol-level differences:")
    print(f"  NEWLY detected by A ({len(newly)}): {', '.join(newly) or 'none'}")
    print(f"  NO LONGER detected under A ({len(lost)}): {', '.join(lost) or 'none'}")

    os.makedirs(OUT, exist_ok=True)
    w = csv.writer(open(f"{OUT}/w1_variantA_compare.csv", "w", newline=""))
    w.writerow(["symbol", "official_detected", "official_firstpass", "official_block",
                "A_detected", "A_firstpass", "A_block", "diff"])
    for s in cohort:
        d = ("newly-detected" if (A[s][0] and not off[s][0]) else
             "lost" if (off[s][0] and not A[s][0]) else "")
        w.writerow([s, off[s][0], off[s][1], off[s][2], A[s][0], A[s][1], A[s][2], d])
    print(f"\nwrote {OUT}/w1_variantA_compare.csv")
    print("(Experimental — hypotheses only. Official TASI-W1 unchanged: rules.yaml + tasi-w1.js.)")


if __name__ == "__main__":
    main()
