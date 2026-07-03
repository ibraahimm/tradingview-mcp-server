#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# EXPERIMENTAL — evidence for the PROPOSED 2026-07-04 TASI-W2 guardrail restoration:
# restore p1m_max=20 (perf_1m < 20, lt) and py_min=-20 (perf_1y > -20, gt); p1m_min
# stays removed. The current canon has no perf_1m/perf_1y predicates, so overrides
# cannot express the candidate — it is built as a clearly-labelled CANDIDATE RULE
# in memory. Never edits official files. Outputs are hypotheses. See TESTING.md.
# ------------------------------------------------------------------------------
"""Forward-return backtest: current TASI-W2 vs the proposed guardrail variant vs the
pre-simplification momentum gates (for context), all on the current canon base.

    python -m research.experiments.w2_guardrails_restore_test research/panel/tadawul_<vintage>.parquet

Same gauntlet as prior tests: dedup signals, market-neutral excess, net 31 bps,
block-bootstrap CI/p (B=5000), Bonferroni-deflated, P(variant>cur).
"""
from __future__ import annotations
import copy
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


def candidate(base: dict, preds_after: list[tuple[str, dict]], params: dict) -> dict:
    """CANDIDATE rule = deepcopy(current canon W2) + inserted predicates. Experiment-only."""
    r = copy.deepcopy(base)
    r["params"].update(params)
    for anchor, pred in preds_after:
        idx = next(i for i, s in enumerate(r["funnel"]) if s["feature"] == anchor)
        r["funnel"].insert(idx + 1, pred)
    return r


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
    w2 = rules["TASI-W2"]

    guard = candidate(w2, [
        ("age_years", {"feature": "perf_1m", "op": "lt", "value": "@p1m_max", "null_action": "drop"}),
        ("perf_6m",   {"feature": "perf_1y", "op": "gt", "value": "@py_min", "null_action": "drop"}),
    ], {"p1m_max": 20, "py_min": -20})
    oldg = candidate(w2, [
        ("age_years", {"feature": "perf_1m", "op": "in_oo", "value": ["@p1m_min", "@p1m_max"], "null_action": "drop"}),
        ("perf_6m",   {"feature": "perf_1y", "op": "gt", "value": "@py_min", "null_action": "drop"}),
    ], {"p1m_min": 0, "p1m_max": 15, "py_min": 0})

    SPECS = [("W2 CUR", w2), ("W2 GUARD", guard), ("W2 OLDGATES", oldg)]
    n_trials = len(SPECS) * len(HOR)
    print(f"\nTASI-W2 GUARDRAIL RESTORATION TEST (market-neutral excess; net cost {COST}bps; "
          f"block bootstrap B={B}; Bonferroni n_trials={n_trials})\n")
    print(f"{'spec':12}{'H':>4}{'n':>6}{'xs%':>8}{'net%':>8}{'boot_p':>8}{'p_defl':>8}   95% CI (xs)")
    kept_store = {}
    for label, rule in SPECS:
        decided = R.evaluate_frame(rule, labeled, None)
        for h in HOR:
            kept = dedup_signals(decided, h)
            kept_store[(label, h)] = kept
            bs = block_bootstrap(kept.get_column("date").to_list(),
                                 kept.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
            net = net_of_cost(bs["mean"], COST) if bs["mean"] is not None else None
            pdef = min(1.0, bs["p_boot"] * n_trials) if bs["p_boot"] is not None else None
            print(f"{label:12}{h:>4}{bs['n']:>6}{f(bs['mean']):>8}{f(net):>6}{f(bs['p_boot'],3):>8}"
                  f"{f(pdef,3):>8}   [{f(bs['ci_low'])}, {f(bs['ci_high'])}]")

    print("\nVARIANT vs CUR — P(variant_xs > cur_xs) via independent block bootstraps:")
    for label in ("W2 GUARD", "W2 OLDGATES"):
        for h in HOR:
            kv, kc = kept_store[(label, h)], kept_store[("W2 CUR", h)]
            p = prob_greater(kv.get_column("date").to_list(), kv.get_column(f"xs_{h}").to_list(),
                             kc.get_column("date").to_list(), kc.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
            dv = block_bootstrap(kv.get_column("date").to_list(), kv.get_column(f"xs_{h}").to_list(), 1, 0)["mean"]
            dc = block_bootstrap(kc.get_column("date").to_list(), kc.get_column(f"xs_{h}").to_list(), 1, 0)["mean"]
            print(f"  {label:12} @{h:>3}d:  variant n={kv.height:<5} xs {f(dv)}   vs   cur n={kc.height:<5} "
                  f"xs {f(dc)}   ->  P(var>cur)={f(p,2)}   (delta {f((dv or 0)-(dc or 0),2)}pp)")

    print("\nReading: P(var>cur)>~0.6 => the guardrails RECOVER per-signal quality vs the gateless "
          "current rule; ~0.5 => no per-signal effect; the OLDGATES row shows how much of the "
          "pre-simplification edge the lighter guardrails recapture.")
    print("(Experimental — hypotheses only. Official TASI-W2 unchanged: rules.yaml + tasi-w2.js.)")


if __name__ == "__main__":
    main()
