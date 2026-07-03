#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Replays the OFFICIAL TASI-W1 rule via the engine (no overrides); never edits rules.yaml or the live JS.
# Per-gate thresholds come FROM the rule spec; the "realistic band" is a declared judgement (below).
# Outputs are HYPOTHESES, not the documented methodology. See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""TASI-W1 60-day ROLLING replay over TASI-W1's INTENDED structural universe, with a full auditable trail.

    python -m research.experiments.w1_replay_60d research/panel/tadawul_<vintage>.parquet

Cohort_d (the intended TASI-W1 universe, recomputed each day) = non-9xxx AND
    age_years>=5  AND  DDmax>=50  AND  belowATH in [40,100]  AND  offLow>=20.
Because the cohort already satisfies those structural gates, the ONLY TASI-W1 gates that can still block a
cohort member are the momentum/perf gates (perf_3m, perf_6m, perf_3y, perf_5y, perf_10y, offlow upper).

Evaluation = last 60 trading days only (PIT, official TASI_W1). For each cohort stock-day we record whether
TASI-W1 fired, every remaining failing gate, the minimum mathematical change to pass, AND whether that change
is a *realistic* methodology tweak vs an *extreme* one. Plus a symbol-level summary with the milestone
chronology that tests the 'violent skip' hypothesis directly.

Outputs (.claude/outputs/): w1_replay_daily.csv, w1_replay_evidence.csv, w1_replay_symbols.csv.
"""
from __future__ import annotations
import csv
import os
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load                                   # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402

EVAL_DAYS = 60
OUT = ".claude/outputs"

# Declared "realistic methodology band": a required change is REALISTIC only if it stays inside intent.
# (A judgement, stated explicitly so it can be challenged — NOT derived from the spec.)
#   key param -> predicate on the stock's feature value x that the change stays realistic.
REALISTIC = {
    "p6m_min": lambda x: x >= -15,     # admit recent launches whose 6M is still mildly negative
    "p6m_max": lambda x: x <= 100,
    "p3m_min": lambda x: x >= 0,        # allow a flat 3M
    "p3m_max": lambda x: x <= 60,       # allow a hotter 3M
    "offlow_max": lambda x: x <= 100,   # allow up to 'doubled off the low'
    # p3y_max / p5y_max / p10y_max: relaxing these admits already-recovered / mature winners ->
    # that redefines 'deep recent correction', so they are NEVER realistic (handled below).
}


def _pname(raw):
    return raw[1:] if isinstance(raw, str) and raw.startswith("@") else None


def diagnose(rule, row):
    """(passed, [ (gate_desc, min_change_desc, realistic_bool) ]) for ALL failing TASI-W1 gates."""
    params = rule["params"]
    fails = []
    for pred in rule["funnel"]:
        if not R._enabled(pred, params):
            continue
        feat, op, raw = pred["feature"], pred["op"], pred["value"]
        x = row.get(feat)
        if x is None:
            if pred.get("null_action") == "drop":
                fails.append((f"{feat}=null", f"{feat} unavailable", False))
            continue
        if op in ("ge", "gt", "le", "lt"):
            v = R._resolve(raw, params)
            if R._OPS[op](x, v):
                continue
            rel = {"ge": "<=", "gt": "<", "le": ">=", "lt": ">"}[op]
            p = _pname(raw)
            fails.append((f"{feat}={x:g} fails {op} {v:g}", f"{p or 'const'} {rel} {x:g}",
                          bool(p in REALISTIC and REALISTIC[p](x))))
        else:
            lo_r, hi_r = raw
            lo, hi = R._resolve(lo_r, params), R._resolve(hi_r, params)
            lo_incl, hi_incl = op in ("in_co", "in_cc"), op == "in_cc"
            if R._OPS[op](x, [lo, hi]):
                continue
            if (x < lo) if lo_incl else (x <= lo):
                p, rel = _pname(lo_r), ("<=" if lo_incl else "<")
                fails.append((f"{feat}={x:g} fails >= {lo:g}", f"{p or 'const'} {rel} {x:g}",
                              bool(p in REALISTIC and REALISTIC[p](x))))
            else:
                p, rel = _pname(hi_r), (">=" if hi_incl else ">")
                fails.append((f"{feat}={x:g} fails < {hi:g}", f"{p or 'const'} {rel} {x:g}",
                              bool(p in REALISTIC and REALISTIC[p](x))))
    return (len(fails) == 0, fails)


def first_where(rows, pred):
    for r in rows:
        if pred(r):
            return r["date"]
    return None


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    feat = compute_value(compute_age_years(build_panel(prices), sm))
    dates = sorted(feat.get_column("date").unique().to_list())
    eval_dates = dates[-EVAL_DAYS:]
    TASI_W1 = R.load_rules()["TASI-W1"]

    # structural cohort universe (non-9xxx + the 5 structural conditions), over the 60 days
    uni = feat.filter(
        pl.col("date").is_in(eval_dates) & (~pl.col("sec_id").str.starts_with("9"))
        & (pl.col("age_years") >= 5) & (pl.col("ddmax") >= 50)
        & (pl.col("below_ath") >= 40) & (pl.col("below_ath") <= 100) & (pl.col("off_low") >= 20))
    dec = R.evaluate_frame(TASI_W1, uni, None)
    rows = {(r["sec_id"], r["date"]): r for r in dec.iter_rows(named=True)}
    cohort_by_day, sym_rows, first_fire = {}, {}, {}
    for (sid, d), r in rows.items():
        cohort_by_day.setdefault(d, []).append(sid)
        sym_rows.setdefault(sid, []).append(r)
        if r["passed"] and (sid not in first_fire or d < first_fire[sid]):
            first_fire[sid] = d
    for sid in sym_rows:
        sym_rows[sid].sort(key=lambda r: r["date"])

    os.makedirs(OUT, exist_ok=True)
    evw = csv.writer(open(f"{OUT}/w1_replay_evidence.csv", "w", newline=""))
    evw.writerow(["date", "symbol", "offLow", "perf_3m", "perf_6m", "perf_3y", "passed_today",
                  "detected_by_today", "n_failed", "failed_gates", "min_changes(realistic?)"])
    dw = csv.writer(open(f"{OUT}/w1_replay_daily.csv", "w", newline=""))
    dw.writerow(["date", "cohort", "detected_cum", "undetected", "undetected_syms"])

    print(f"evaluation period: last {EVAL_DAYS} trading days, {eval_dates[0]} .. {eval_dates[-1]}")
    print("cohort_d = non-9xxx & age>=5 & DDmax>=50 & belowATH in[40,100] & offLow>=20\n")
    print(f"{'date':12}{'cohort':>7}{'det':>5}{'undet':>6}")
    for d in eval_dates:
        cohort = cohort_by_day.get(d, [])
        det = [s for s in cohort if s in first_fire and first_fire[s] <= d]
        undet = [s for s in cohort if s not in det]
        dw.writerow([d, len(cohort), len(det), len(undet), ";".join(sorted(undet))])
        print(f"{str(d):12}{len(cohort):>7}{len(det):>5}{len(undet):>6}")
        for s in sorted(cohort):                       # ALL cohort stock-days (detected AND not)
            r = rows[(s, d)]
            _, fails = diagnose(TASI_W1, r)
            mc = " | ".join(f"{c} [{'realistic' if ok else 'extreme'}]" for _, c, ok in fails)
            evw.writerow([d, s, f"{r['off_low']:.0f}",
                          f"{r['perf_3m']:.0f}" if r['perf_3m'] is not None else "",
                          f"{r['perf_6m']:.0f}" if r['perf_6m'] is not None else "",
                          f"{r['perf_3y']:.0f}" if r['perf_3y'] is not None else "",
                          r["passed"], (s in first_fire and first_fire[s] <= d),
                          len(fails), " | ".join(f for f, _, _ in fails), mc])

    # ---- symbol-level summary with milestone chronology (the skip-hypothesis evidence) ----
    sw = csv.writer(open(f"{OUT}/w1_replay_symbols.csv", "w", newline=""))
    hdr = ["symbol", "cohort_days", "detected", "first_pass", "undetected_days", "dominant_block",
           "realistic_fix_exists", "first_offLow>=20", "first_P3M>=5", "first_P6M>0",
           "first_offLow>60", "first_P3M>40", "skip_window?"]
    sw.writerow(hdr)
    print(f"\nSYMBOL SUMMARY ({len(sym_rows)} symbols ever in the structural cohort) — chronology tests the skip:")
    print(f"{'sym':6}{'cohD':>5}{'det':>4}{'firstPass':>12}  {'block':>9} {'realFix':>8}  "
          f"{'offL>=20':>10}{'P3M>=5':>10}{'P6M>0':>10}{'offL>60':>10}{'P3M>40':>10}  skip")
    from collections import Counter
    summary = []
    for sid, rs in sym_rows.items():
        fp = first_fire.get(sid)
        undet_rows = [r for r in rs if not (sid in first_fire and r["date"] >= fp)] if fp else rs
        blocks, realistic_any = Counter(), False
        for r in undet_rows:
            _, fails = diagnose(TASI_W1, r)
            for _, c, ok in fails:
                blocks[c.split()[0]] += 1
                realistic_any = realistic_any or ok
        m_off20 = first_where(rs, lambda r: r["off_low"] is not None and r["off_low"] >= 20)
        m_p3m5 = first_where(rs, lambda r: r["perf_3m"] is not None and r["perf_3m"] >= 5)
        m_p6m0 = first_where(rs, lambda r: r["perf_6m"] is not None and r["perf_6m"] > 0)
        m_off60 = first_where(rs, lambda r: r["off_low"] is not None and r["off_low"] > 60)
        m_p3m40 = first_where(rs, lambda r: r["perf_3m"] is not None and r["perf_3m"] > 40)
        lower_met = max([d for d in (m_p3m5, m_p6m0) if d]) if (m_p3m5 and m_p6m0) else None
        upper = min([d for d in (m_off60, m_p3m40) if d], default=None)
        # genuine violent skip: the lower gates DID jointly get met, but an upper cap had already
        # breached by then (so no valid window). 'lower never met' is a DIFFERENT case (too-recent).
        skip = bool(lower_met is not None and upper is not None and upper <= lower_met)
        dom = blocks.most_common(1)[0][0] if blocks else "(detected/none)"
        summary.append((sid, len(rs), bool(fp), fp, len(undet_rows), dom, realistic_any,
                        m_off20, m_p3m5, m_p6m0, m_off60, m_p3m40, skip))
    for row in sorted(summary, key=lambda x: (x[2], str(x[3]))):   # undetected first, then by pass date
        sid, cohd, det, fp, ud, dom, rf, a20, a5, a0, a60, a40, skip = row
        sw.writerow([sid, cohd, det, fp, ud, dom, rf, a20, a5, a0, a60, a40, skip])
        print(f"{sid:6}{cohd:>5}{('Y' if det else 'n'):>4}{str(fp) if fp else '—':>12}  {dom:>9} "
              f"{('yes' if rf else 'no'):>8}  {str(a20):>10}{str(a5):>10}{str(a0):>10}"
              f"{str(a60):>10}{str(a40):>10}  {'SKIP' if skip else ''}")

    print(f"\nfiles: {OUT}/w1_replay_daily.csv · w1_replay_evidence.csv (incl. detected) · w1_replay_symbols.csv")
    print("realistic band (declared, challengeable): p6m_min>=-15, p3m_min>=0, p3m_max<=60, offlow_max<=100;")
    print("  p3y_max/p5y_max/p10y_max relaxations are 'extreme' (they redefine deep-recent-correction).")
    print("(Experimental — hypotheses only. Official TASI_W1 = rules.yaml + tasi-w1.js.)")


if __name__ == "__main__":
    main()
