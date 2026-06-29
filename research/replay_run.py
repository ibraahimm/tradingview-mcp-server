#!/usr/bin/env python3
"""Replay the documented W1/W2 tracker methodology across the full historical panel.

    python -m research.replay_run research/panel/tadawul_<vintage>.parquet

Faithful replay (not a new strategy): generate ledger events from the engine's W1/W2 pass-rows under
the documented daily-cadence adaptation, then classify each symbol's journey with the PROVEN tracker
state machine. Reports the historical base rates today's live tracker can be read against.
"""
from __future__ import annotations
import os
import sys
from statistics import median

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load                                   # noqa: E402
from research.engine.panel import build_panel                       # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402
from research.backtest.replay import generate_ledger, journey_outcomes  # noqa: E402


def pct(x):
    return f"{100*x:.0f}%"


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(pl.col("date").min().alias("list_date"),
                                       pl.col("date").max().alias("last_date"))
    print(f"loaded {prices.height:,} rows / {prices['sec_id'].n_unique()} secs; building panel ...")
    feat = compute_value(compute_age_years(build_panel(prices), sm))
    rules = R.load_rules()
    dW1 = R.evaluate_frame(rules["W1"], feat, None)
    dW2 = R.evaluate_frame(rules["W2"], feat, None)
    events = generate_ledger({"W1": dW1, "W2": dW2})
    jr = journey_outcomes(events)
    print(f"generated {len(events):,} historical events; {len(jr)} symbol journeys "
          f"(daily-cadence replay; date range {events[0]['date']}..{max(e['date'] for e in events)})\n")

    w1 = [j for j in jr if j["entered_w1"]]
    promoted = [j for j in w1 if j["promoted"]]
    failed = [j for j in w1 if j["terminal"] == "FAILED"]
    w1only = [j for j in w1 if not j["promoted"]]

    def gains(js):
        return [j["max_gain"] for j in js if j["max_gain"] is not None]

    print("HISTORICAL BASE RATES (documented methodology replayed through history)")
    print(f"  W1-entry journeys ............ {len(w1)}")
    print(f"  promoted W1->W2 .............. {len(promoted)} ({pct(len(promoted)/len(w1))})")
    print(f"  terminal FAILED ............. {len(failed)} ({pct(len(failed)/len(w1))})")
    print(f"  terminal-state mix .......... " +
          ", ".join(f"{s}:{sum(1 for j in w1 if j['terminal']==s)}"
                    for s in ("ACTIVE-W1", "ACTIVE-W2", "FAILED", "EXPIRED", "GRAD★")))

    def line(label, js):
        g = gains(js)
        if not g:
            print(f"  {label:24} n=0")
            return
        print(f"  {label:24} n={len(js):<4} max-gain median {median(g):+.1f}%  "
              f">+20%: {pct(sum(x>20 for x in g)/len(g))}  >+50%: {pct(sum(x>50 for x in g)/len(g))}  "
              f">+100%: {pct(sum(x>100 for x in g)/len(g))}")

    print("\nPeak gainSinceSignal achieved while the journey was ACTIVE (tracker's own metric, no forward look):")
    line("all W1 entries", w1)
    line("  promoted (W1->W2)", promoted)
    line("  W1-only (never promoted)", w1only)
    line("  terminal FAILED", failed)

    print("\nINTERPRETATION: promotion (reaching W2) is the documented progression signal — compare the "
          "promoted vs W1-only peak-gain rows. FAILED journeys are the falling-knife outcome.")
    print("Connect to today's live tracker (Part 4) using these base rates.")


if __name__ == "__main__":
    main()
