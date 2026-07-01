#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Uses runtime params_overrides and/or observable candidate pre-filters; it never edits
# rules.yaml or the live JS. Outputs are HYPOTHESES, not the documented methodology.
# See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""Focused A/B: does the 10% extension cap help in the EARLY WAVES (W1 & W2), over the LAST 3 MONTHS?

    python -m research.ext_cap_recent research/panel/tadawul_<vintage>.parquet

Population = W1 entries (cap = close/EMA60 <= 10%) UNION W2 entries (cap = close/EMA21 <= 10%), restricted
to entries in the last ~3 months. We evaluate both screens with the cap DISABLED (ext60_max/ext21_max =
999), then split each entry by its extension value:
    WITH cap     = ext <= 10%   (what the live screen admits)
    WITHOUT cap  = all entries  (capped + the ext>10% names the live screen would reject)
Outcome: fwd 20-trading-day return (clean, where available) + return-to-data-end (captures very recent
entries like the 8280 case). Small sample by design — illustrative for the recent cohort, not a deflated
20-year claim.
"""
from __future__ import annotations
import os
import sys
from datetime import date
from statistics import mean, median

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load, _load_terminals, CUT             # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402
from research.backtest.event_study import label_forward_returns     # noqa: E402
from research.backtest.rigor import with_td_idx, dedup_signals      # noqa: E402

HOR = [10, 20]
WINDOW_START = date(2026, 3, 25)   # ~3 months before the 2026-06-25 data end
CAP = 10.0


def _summ(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n=0"
    return (f"n={len(vals):<3} mean {mean(vals):+5.1f}%  median {median(vals):+5.1f}%  "
            f"hit {100*sum(v > 0 for v in vals)/len(vals):.0f}%")


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(
        pl.col("date").min().alias("list_date"), pl.col("date").max().alias("last_date")
    ).with_columns(delist_date=pl.when(pl.col("last_date") < CUT).then(pl.col("last_date")).otherwise(None))
    tv = _load_terminals()
    sm = sm.join(pl.DataFrame({"sec_id": list(tv), "terminal_value": list(tv.values())},
                              schema={"sec_id": pl.Utf8, "terminal_value": pl.Float64}), on="sec_id", how="left")
    feat = with_td_idx(label_forward_returns(
        compute_value(compute_age_years(build_panel(prices), sm)), sm, horizons=HOR))
    end = feat.get_column("date").max()
    lastc = (feat.sort(["sec_id", "td_idx"]).group_by("sec_id")
             .agg(pl.col("close").last().alias("last_close"), pl.col("td_idx").max().alias("last_td")))
    win = feat.filter(pl.col("date") >= WINDOW_START).join(lastc, on="sec_id", how="left")
    print(f"data end {end}; window >= {WINDOW_START} ({win.height} name-days)\n")

    rules = R.load_rules()
    rows = []
    for wave, ov, extcol in (("W1", {"ext60_max": 999}, "ext60"), ("W2", {"ext21_max": 999}, "ema21gap")):
        decided = R.evaluate_frame(rules[wave], win, ov)
        kept = dedup_signals(decided, 20)
        for r in kept.iter_rows(named=True):
            rows.append({"sym": r["sec_id"], "wave": wave, "date": r["date"], "ext": r[extcol],
                         "fwd20": r.get("fwd_20"), "fwd10": r.get("fwd_10"),
                         "ret_end": (r["last_close"] / r["close"] - 1) * 100 if r["close"] else None,
                         "held": r["last_td"] - r["td_idx"]})
    rows = [r for r in rows if r["ext"] is not None]
    capped = [r for r in rows if r["ext"] <= CAP]
    rejected = [r for r in rows if r["ext"] > CAP]

    print(f"EARLY-WAVE (W1∪W2) entries in window: {len(rows)}  "
          f"(WITH cap ext<=10%: {len(capped)} | rejected ext>10%: {len(rejected)})\n")

    print("fwd 20-trading-day return (entries old enough to have it):")
    print(f"  WITHOUT cap (all)     : {_summ([r['fwd20'] for r in rows])}")
    print(f"  WITH cap   (ext<=10%) : {_summ([r['fwd20'] for r in capped])}")
    print(f"  rejected   (ext>10%)  : {_summ([r['fwd20'] for r in rejected])}")
    print("\nreturn to data-end (all entries incl. very recent; variable hold):")
    print(f"  WITHOUT cap (all)     : {_summ([r['ret_end'] for r in rows])}")
    print(f"  WITH cap   (ext<=10%) : {_summ([r['ret_end'] for r in capped])}")
    print(f"  rejected   (ext>10%)  : {_summ([r['ret_end'] for r in rejected])}")

    print(f"\nThe ext>10% names the cap REJECTS (did they underperform?) :")
    print(f"  {'sym':6}{'wave':5}{'date':12}{'ext%':>7}{'fwd20%':>8}{'ret_end%':>9}{'held':>5}")
    for r in sorted(rejected, key=lambda x: -x["ext"]):
        f20 = f"{r['fwd20']:+.1f}" if r["fwd20"] is not None else "  —"
        print(f"  {r['sym']:6}{r['wave']:5}{str(r['date']):12}{r['ext']:>7.1f}{f20:>8}"
              f"{r['ret_end']:>9.1f}{r['held']:>5}")
    print("\nReading: if WITH-cap > WITHOUT-cap and rejected underperforms, the cap helped in this recent "
          "early-wave cohort. (Small n — recent-cohort illustration, not a deflated multi-year result.)")


if __name__ == "__main__":
    main()
