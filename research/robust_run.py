#!/usr/bin/env python3
"""Robustness pass: net-of-cost excess + block-bootstrap (cluster-robust) inference for TASI-W1/TASI-W2/TASI-W3.

    python -m research.robust_run research/panel/tadawul_<vintage>.parquet

The honest last gate before "tradeable": does the TASI-W2/TASI-W3 excess survive (a) transaction costs and
(b) inference that respects time/cross-sectional clustering (block bootstrap), not the optimistic
i.i.d. t-stat?
"""
from __future__ import annotations
import os
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load, _load_terminals, CUT          # noqa: E402
from research.engine.panel import build_panel                      # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                             # noqa: E402
from research.backtest.event_study import label_forward_returns    # noqa: E402
from research.backtest.rigor import add_excess, with_td_idx, dedup_signals  # noqa: E402
from research.backtest.robust import block_bootstrap, net_of_cost   # noqa: E402

HORIZONS = [20, 60, 120]
COST_BPS = 31          # Saudi round-trip ~ regulated commission both sides (~0.31%)
B = 5000


def f(x, d=2):
    return "  n/a" if x is None else f"{x:+.{d}f}"


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(
        pl.col("date").min().alias("list_date"), pl.col("date").max().alias("last_date")
    ).with_columns(delist_date=pl.when(pl.col("last_date") < CUT).then(pl.col("last_date")).otherwise(None))
    tv = _load_terminals()
    sm = sm.join(pl.DataFrame({"sec_id": list(tv), "terminal_value": list(tv.values())},
                              schema={"sec_id": pl.Utf8, "terminal_value": pl.Float64}), on="sec_id", how="left")
    print(f"loaded {prices.height:,} rows / {prices['sec_id'].n_unique()} secs; building panel ...")
    panel = build_panel(prices)
    labeled = with_td_idx(add_excess(
        label_forward_returns(compute_value(compute_age_years(panel, sm)), sm, horizons=HORIZONS), HORIZONS))

    print(f"\nNET-OF-COST + BLOCK-BOOTSTRAP (by month, B={B}); round-trip cost = {COST_BPS} bps.\n")
    print(f"{'rule':4} {'H':>4} {'n':>5} {'gross%':>7} {'net%':>6} {'boot_p':>7} "
          f"{'95% CI (gross)':>18}  net>0 @95%?")
    rules = R.load_rules()
    for rule in ("TASI-W2", "TASI-W3", "TASI-W1"):
        decided = R.evaluate_frame(rules[rule], labeled, None)
        for h in HORIZONS:
            kept = dedup_signals(decided, h)
            bs = block_bootstrap(kept.get_column("date").to_list(),
                                 kept.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
            net = net_of_cost(bs["mean"], COST_BPS) if bs["mean"] is not None else None
            # net is significantly > 0 at 95% iff the (gross) bootstrap lower CI exceeds the cost
            net_sig = bs["ci_low"] is not None and (bs["ci_low"] - COST_BPS / 100.0) > 0
            print(f"{rule:4} {h:>4} {bs['n']:>5} {f(bs['mean']):>7} {f(net):>6} {f(bs['p_boot'],3):>7} "
                  f"[{f(bs['ci_low'])}, {f(bs['ci_high'])}]   {'YES' if net_sig else 'no'}")

    print("\nReading: 'boot_p' is cluster-robust (block) — compare to the naive rigor t-test p.")
    print("'net>0 @95%?' = does the bootstrap 95% CI stay above the transaction cost.")
    print("\nDONE.")


if __name__ == "__main__":
    main()
