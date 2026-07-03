#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — evidence for the PROPOSED promotion of 2026-07-03:
#   (a) offlow_min 35 -> 30 on TASI-W1 and TASI-W2 (partial revert of D-2026-07-01-01),
#   (b) TASI-W2 end-state: offlow_min 30 AND p1m/py gates removed (see
#       w2_momentum_gate_removal.py for the gates-only test).
# Uses runtime overrides only; never edits official files. Outputs are hypotheses.
# See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""Forward-return backtest of the proposed offlow_min 35->30 change and the full
proposed TASI-W2 end-state, vs current canon.

    python -m research.experiments.offlow30_promotion_test research/panel/tadawul_<vintage>.parquet

Same gauntlet as w1w2_param_forward_backtest: non-overlapping signals, market-neutral
excess, net-of-cost (31 bps), block-bootstrap CI/p, Bonferroni-deflated, plus
P(cur > variant) per horizon. Gate REMOVAL approximated by widening to +/-1e18
(exact for the eligible >=5y universe; see w2_momentum_gate_removal.py note).
"""
from __future__ import annotations
import os
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load, _load_terminals, CUT                    # noqa: E402
from research.engine.panel import build_panel                              # noqa: E402
from research.engine.screen import compute_age_years, compute_value        # noqa: E402
from research.engine import rules as R                                     # noqa: E402
from research.backtest.event_study import label_forward_returns            # noqa: E402
from research.backtest.rigor import add_excess, with_td_idx, dedup_signals  # noqa: E402
from research.backtest.robust import block_bootstrap, net_of_cost, prob_greater  # noqa: E402

HOR = [20, 60, 120]
COST = 31
B = 5000
WIDE = 1e18
SPECS = [
    ("W1 CUR", "TASI-W1", None),
    ("W1 OL30", "TASI-W1", {"offlow_min": 30}),
    ("W2 CUR", "TASI-W2", None),
    ("W2 OL30", "TASI-W2", {"offlow_min": 30}),
    ("W2 PROP", "TASI-W2", {"offlow_min": 30, "p1m_min": -WIDE, "p1m_max": WIDE, "py_min": -WIDE}),
]
PAIRS = [("W1 CUR", "W1 OL30"), ("W2 CUR", "W2 OL30"), ("W2 CUR", "W2 PROP")]


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
    labeled = with_td_idx(add_excess(
        label_forward_returns(compute_value(compute_age_years(build_panel(prices), sm)), sm, horizons=HOR), HOR))
    rules = R.load_rules()

    n_trials = len(SPECS) * len(HOR)
    print(f"\nOFFLOW30 + W2-PROPOSED PROMOTION TEST (market-neutral excess; net cost {COST}bps; "
          f"block bootstrap B={B}; Bonferroni n_trials={n_trials})\n")
    print(f"{'spec':9}{'H':>4}{'n':>6}{'xs%':>8}{'net%':>8}{'boot_p':>8}{'p_defl':>8}   95% CI (xs)")
    kept_store = {}
    for label, rule, ov in SPECS:
        decided = R.evaluate_frame(rules[rule], labeled, ov)
        for h in HOR:
            kept = dedup_signals(decided, h)
            kept_store[(label, h)] = kept
            bs = block_bootstrap(kept.get_column("date").to_list(),
                                 kept.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
            net = net_of_cost(bs["mean"], COST) if bs["mean"] is not None else None
            pdef = min(1.0, bs["p_boot"] * n_trials) if bs["p_boot"] is not None else None
            print(f"{label:9}{h:>4}{bs['n']:>6}{f(bs['mean']):>8}{f(net):>6}{f(bs['p_boot'],3):>8}"
                  f"{f(pdef,3):>8}   [{f(bs['ci_low'])}, {f(bs['ci_high'])}]")

    print("\nCUR vs VARIANT — P(cur_xs > variant_xs) via independent block bootstraps:")
    for cur, var in PAIRS:
        for h in HOR:
            kc, kv = kept_store[(cur, h)], kept_store[(var, h)]
            p = prob_greater(kc.get_column("date").to_list(), kc.get_column(f"xs_{h}").to_list(),
                             kv.get_column("date").to_list(), kv.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
            dc = block_bootstrap(kc.get_column("date").to_list(), kc.get_column(f"xs_{h}").to_list(), 1, 0)["mean"]
            dv = block_bootstrap(kv.get_column("date").to_list(), kv.get_column(f"xs_{h}").to_list(), 1, 0)["mean"]
            print(f"  {cur:8} vs {var:8} @{h:>3}d:  cur n={kc.height:<5} xs {f(dc)}   variant n={kv.height:<5} "
                  f"xs {f(dv)}   ->  P(cur>var)={f(p,2)}   (delta {f((dc or 0)-(dv or 0),2)}pp)")

    print("\nReading: P(cur>var)~0.5 => the variant is return-neutral (a recall/selectivity choice, "
          "not an edge change); >~0.6 => the variant LOSES per-signal quality; <~0.4 => variant improves it.")
    print("(Experimental — hypotheses only. Official TASI-W1/TASI-W2 unchanged: rules.yaml + live JS.)")


if __name__ == "__main__":
    main()
