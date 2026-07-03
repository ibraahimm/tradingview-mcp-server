#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — evidence for the PROPOSED removal of p1m_min / p1m_max / py_min
# from TASI-W2 (directive of 2026-07-03, pending promotion). Uses runtime overrides
# only; never edits official files. Outputs are hypotheses, not methodology.
# See research/spec/TESTING.md.
# ------------------------------------------------------------------------------
"""Forward-return backtest: current official TASI-W2 vs TASI-W2 with the Perf.1M band
and the Perf.1Y>0 gate disabled.

    python -m research.experiments.w2_momentum_gate_removal research/panel/tadawul_<vintage>.parquet

Method (same gauntlet as w1w2_param_forward_backtest): full-history event study,
non-overlapping (dedup) signals, market-neutral EXCESS returns, net-of-cost (31 bps),
block-bootstrap CI/p, Bonferroni-deflated, plus P(cur > nogate) per horizon.

Override note: predicate REMOVAL is approximated by widening to ±1e18. The only semantic
difference is null handling (a null perf_1m/perf_1y would still drop under the override,
but would pass under true removal). For the eligible universe (age >= 5y) perf_1m/perf_1y
are never null, so the approximation is exact in practice.
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
    ("W2 CUR", "TASI-W2", None),
    ("W2 NOGATE", "TASI-W2", {"p1m_min": -WIDE, "p1m_max": WIDE, "py_min": -WIDE}),
]


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
    print(f"\nTASI-W2 MOMENTUM-GATE REMOVAL TEST (market-neutral excess; net cost {COST}bps; "
          f"block bootstrap B={B}; Bonferroni n_trials={n_trials})\n")
    print(f"{'spec':10}{'H':>4}{'n':>6}{'xs%':>8}{'net%':>8}{'boot_p':>8}{'p_defl':>8}   95% CI (xs)")
    kept_store = {}
    raw_counts = {}
    for label, rule, ov in SPECS:
        decided = R.evaluate_frame(rules[rule], labeled, ov)
        raw_counts[label] = decided.filter(decided["passed"]).height
        for h in HOR:
            kept = dedup_signals(decided, h)
            kept_store[(label, h)] = kept
            bs = block_bootstrap(kept.get_column("date").to_list(),
                                 kept.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
            net = net_of_cost(bs["mean"], COST) if bs["mean"] is not None else None
            pdef = min(1.0, bs["p_boot"] * n_trials) if bs["p_boot"] is not None else None
            print(f"{label:10}{h:>4}{bs['n']:>6}{f(bs['mean']):>8}{f(net):>6}{f(bs['p_boot'],3):>8}"
                  f"{f(pdef,3):>8}   [{f(bs['ci_low'])}, {f(bs['ci_high'])}]")

    print(f"\nRaw passed signal-bars: CUR {raw_counts['W2 CUR']:,} vs NOGATE {raw_counts['W2 NOGATE']:,} "
          f"(+{raw_counts['W2 NOGATE'] - raw_counts['W2 CUR']:,} admitted by removal)")

    print("\nCUR vs NOGATE — does keeping the gates earn MORE per signal? "
          "P(cur_xs > nogate_xs) via independent block bootstraps:")
    for h in HOR:
        kc, kn = kept_store[("W2 CUR", h)], kept_store[("W2 NOGATE", h)]
        p = prob_greater(kc.get_column("date").to_list(), kc.get_column(f"xs_{h}").to_list(),
                         kn.get_column("date").to_list(), kn.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
        dc = block_bootstrap(kc.get_column("date").to_list(), kc.get_column(f"xs_{h}").to_list(), 1, 0)["mean"]
        dn = block_bootstrap(kn.get_column("date").to_list(), kn.get_column(f"xs_{h}").to_list(), 1, 0)["mean"]
        print(f"  @{h:>3}d:  cur n={kc.height:<5} xs {f(dc)}   vs   nogate n={kn.height:<5} xs {f(dn)}"
              f"   ->  P(cur>nogate)={f(p,2)}   (delta {f((dc or 0)-(dn or 0),2)}pp)")

    print("\nReading: P(cur>nogate)>~0.6 => the gates ADD per-signal quality (removal loses edge); "
          "~0.5 => the gates are inert (removal only widens the funnel); <~0.4 => the gates HURT.")
    print("(Experimental — hypotheses only. Official TASI-W2 unchanged: rules.yaml + tasi-w2.js.)")


if __name__ == "__main__":
    main()
