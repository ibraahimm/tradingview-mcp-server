#!/usr/bin/env python3
"""Rigor pass on real data for W1/W2/W3: market-neutral excess, non-overlapping signals,
walk-forward, Bonferroni deflation. Includes the ext60_max A/B for W1.

    python -m research.rigor_run <companies_dir>

INDICATIVE-but-rigorous: adjusted, survivorship-inclusive data with curated delisting terminals.
"""
from __future__ import annotations
import datetime
import os
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load, _load_terminals, CUT          # noqa: E402
from research.engine.panel import build_panel                      # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                             # noqa: E402
from research.backtest.event_study import label_forward_returns    # noqa: E402
from research.backtest.rigor import add_excess, with_td_idx, dedup_signals, study  # noqa: E402
from research.backtest.governance import summary_stats, bonferroni  # noqa: E402

HORIZONS = [20, 60, 120]
# (rule, config label, params_override)
SPECS = [("W1", "default", None), ("W1", "ext60 OFF", {"ext60_max": 999}),
         ("W2", "default", None), ("W3", "default", None)]
WF_CUTS = [datetime.date(2010, 1, 1), datetime.date(2015, 1, 1),
           datetime.date(2020, 1, 1), datetime.date(2026, 7, 1)]


def f(x, d=2):
    return "  n/a" if x is None else f"{x:+.{d}f}"


def walkforward(kept, horizon):
    prev, out = None, []
    for c in WF_CUTS:
        w = kept.filter(pl.col("date") <= c) if prev is None else kept.filter((pl.col("date") > prev) & (pl.col("date") <= c))
        out.append((c, summary_stats([v for v in w.get_column(f"xs_{horizon}").to_list() if v is not None])))
        prev = c
    return out


def main():
    cdir = sys.argv[1]
    prices = load(cdir)
    sm = prices.group_by("sec_id").agg(
        pl.col("date").min().alias("list_date"), pl.col("date").max().alias("last_date")
    ).with_columns(delist_date=pl.when(pl.col("last_date") < CUT).then(pl.col("last_date")).otherwise(None))
    tv = _load_terminals()
    sm = sm.join(pl.DataFrame({"sec_id": list(tv), "terminal_value": list(tv.values())},
                              schema={"sec_id": pl.Utf8, "terminal_value": pl.Float64}), on="sec_id", how="left")

    print(f"loaded {prices.height:,} rows / {prices['sec_id'].n_unique()} secs / "
          f"{prices['date'].min()}->{prices['date'].max()}; building panel ...")
    panel = build_panel(prices)
    labeled = with_td_idx(add_excess(
        label_forward_returns(compute_value(compute_age_years(panel, sm)), sm, horizons=HORIZONS), HORIZONS))

    n_trials = len(SPECS) * len(HORIZONS)
    print(f"\nMARKET-NEUTRAL EXCESS, NON-OVERLAPPING signals, deflated by n_trials={n_trials}:\n")
    print(f"{'rule':4} {'config':10} {'H':>4} {'raw':>7} {'indep':>6} {'mean_xs%':>9} {'t':>6} {'p':>6} {'p_defl':>7}")
    rules = R.load_rules()
    a60 = {}
    wf = {}
    for rule, cfg, ov in SPECS:
        decided = R.evaluate_frame(rules[rule], labeled, ov)
        for h in HORIZONS:
            st = study(decided, h, excess=True)
            if h == 60:
                a60[(rule, cfg)] = st
            print(f"{rule:4} {cfg:10} {h:>4} {st['raw_signals']:>7} {st['independent']:>6} "
                  f"{f(st['mean']):>9} {f(st['t']):>6} {f(st['p'],3):>6} {f(bonferroni(st['p'], n_trials),3):>7}")
        if cfg == "default":
            wf[rule] = walkforward(dedup_signals(decided, 60), 60)
        del decided

    print("\next60_max A/B for W1 @ 60d (the original question):")
    g, o = a60[("W1", "default")], a60[("W1", "ext60 OFF")]
    print(f"   gate on  +{g['mean']:.2f}% (n={g['independent']})  |  gate off +{o['mean']:.2f}% (n={o['independent']})"
          f"  |  delta {f((g['mean'] or 0) - (o['mean'] or 0))} pp")

    for rule in ("W1", "W2", "W3"):
        print(f"\nWalk-forward {rule} (default, 60d market-neutral excess):")
        for c, st in wf[rule]:
            print(f"   <= {c}:  n={st['n']:>4}  mean_xs {f(st['mean'])}%  t {f(st['t'])}")

    print("\nDONE (indicative-rigorous; market-neutral, deflated, OOS).")


if __name__ == "__main__":
    main()
