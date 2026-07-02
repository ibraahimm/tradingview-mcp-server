#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — methodology-improvement exploration (NOT official methodology).
# Uses runtime params_overrides and/or observable candidate pre-filters; it never edits
# rules.yaml or the live JS. Outputs are HYPOTHESES, not the documented methodology.
# See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""Day-by-day path from entry for the cap-REJECTED (ext>10%) early-wave entries in the last 3 months.

    python -m research.ext_cap_paths research/panel/tadawul_<vintage>.parquet

A single 20-day endpoint hides the intra-window path (a stretched name may pull back first — the cap's
mean-reversion thesis — then recover, or vice-versa). This prints cumulative return from each entry,
trading day 0..20 (and to data end), so the trajectory is visible.
"""
from __future__ import annotations
import os
import sys
from datetime import date

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load                                   # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402
from research.backtest.rigor import with_td_idx, dedup_signals      # noqa: E402

WINDOW_START = date(2026, 3, 25)
CAP = 10.0
NDAYS = 20


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    feat = with_td_idx(compute_value(compute_age_years(build_panel(prices), sm)))
    # per-symbol sorted (td_idx -> close)
    closes: dict = {}
    for sid, td, cl in feat.select(["sec_id", "td_idx", "close"]).iter_rows():
        closes.setdefault(sid, {})[td] = cl
    win = feat.filter(pl.col("date") >= WINDOW_START)

    rules = R.load_rules()
    rejected = []
    for wave, ov, extcol in (("TASI-W1", {"ext60_max": 999}, "ext60"), ("TASI-W2", {"ext21_max": 999}, "ema21gap")):
        kept = dedup_signals(R.evaluate_frame(rules[wave], win, ov), 20)
        for r in kept.iter_rows(named=True):
            if r[extcol] is not None and r[extcol] > CAP:
                rejected.append({"sym": r["sec_id"], "wave": wave, "date": r["date"],
                                 "ext": r[extcol], "td": r["td_idx"]})

    def path(sym, td0):
        c = closes[sym]
        last = max(c)
        e = c[td0]
        seq = [((c[t] / e - 1) * 100) for t in range(td0, min(td0 + NDAYS, last) + 1) if t in c]
        to_end = (c[last] / e - 1) * 100
        return seq, to_end

    # order by realized to-end gain, winners first
    enr = []
    for x in rejected:
        seq, te = path(x["sym"], x["td"])
        x["seq"], x["to_end"] = seq, te
        enr.append(x)
    enr.sort(key=lambda x: -x["to_end"])

    print(f"Cap-rejected (ext>10%) early-wave entries, day-by-day cumulative % from entry "
          f"(d0=entry .. d{NDAYS}); window >= {WINDOW_START}, data end td-based.\n")
    for x in enr:
        seq = x["seq"]
        days = "".join(f"{v:>6.1f}" for v in seq)
        mn = min(seq); mx = max(seq)
        mn_d = seq.index(mn); mx_d = seq.index(mx)
        at20 = seq[NDAYS] if len(seq) > NDAYS else None
        a20 = f"{at20:+.1f}" if at20 is not None else "n/a(recent)"
        print(f"{x['sym']:5} {x['wave']} {x['date']} ext{x['ext']:>5.1f}%  "
              f"min {mn:+.1f}@d{mn_d}  max {mx:+.1f}@d{mx_d}  @20d {a20}  toEnd {x['to_end']:+.1f}%")
        print(f"      d0..: {days}")
    print("\nReading: a stretched name that dips early (min at a low d) then climbs = the cap would have "
          "saved you the dip but cost you the recovery. One that rises straight = pure missed winner.")


if __name__ == "__main__":
    main()
