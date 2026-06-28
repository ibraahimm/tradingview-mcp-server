#!/usr/bin/env python3
"""Rigor pass on real data: market-neutral excess returns, non-overlapping signals, walk-forward,
Bonferroni deflation — and the ext60_max A/B (the original question), now on real Saudi data.

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
CONFIGS = {"W1 (ext60_max=10)": None, "W1 (ext60 OFF)": {"ext60_max": 999}}


def f(x, d=2):
    return "  n/a" if x is None else f"{x:+.{d}f}"


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

    n_trials = len(CONFIGS) * len(HORIZONS)
    print(f"\nMARKET-NEUTRAL EXCESS return on NON-OVERLAPPING signals (deflated by n_trials={n_trials}):\n")
    print(f"{'config':20} {'H':>4} {'raw':>7} {'indep':>6} {'mean_xs%':>9} {'t':>7} {'p':>7} {'p_defl':>7}")
    rules = R.load_rules()
    studies = {}
    for cname, ov in CONFIGS.items():
        decided = R.evaluate_frame(rules["W1"], labeled, ov)
        for h in HORIZONS:
            st = study(decided, h, excess=True)
            studies[(cname, h)] = st
            print(f"{cname:20} {h:>4} {st['raw_signals']:>7} {st['independent']:>6} "
                  f"{f(st['mean']):>9} {f(st['t']):>7} {f(st['p'],3):>7} {f(bonferroni(st['p'], n_trials),3):>7}")

    print("\next60_max A/B at 60d (does the ceiling improve out-of-sample excess?):")
    a, b = studies[("W1 (ext60_max=10)", 60)], studies[("W1 (ext60 OFF)", 60)]
    print(f"   with ext60_max=10 : mean_xs {f(a['mean'])}%  (indep n={a['independent']})")
    print(f"   ext60 OFF         : mean_xs {f(b['mean'])}%  (indep n={b['independent']})")
    print(f"   delta (gate − off): {f((a['mean'] or 0) - (b['mean'] or 0))} pp")

    print("\nWalk-forward (W1 ext60_max=10, 60d, market-neutral excess, per period):")
    decided = R.evaluate_frame(rules["W1"], labeled, None)
    kept = dedup_signals(decided, 60)
    prev = None
    for c in [datetime.date(2010, 1, 1), datetime.date(2015, 1, 1), datetime.date(2020, 1, 1), datetime.date(2026, 7, 1)]:
        w = kept.filter(pl.col("date") <= c) if prev is None else kept.filter((pl.col("date") > prev) & (pl.col("date") <= c))
        vals = [v for v in w.get_column("xs_60").to_list() if v is not None]
        st = summary_stats(vals)
        print(f"   <= {c}:  n={st['n']:>4}  mean_xs {f(st['mean'])}%  t {f(st['t'])}")
        prev = c
    print("\nDONE (indicative-rigorous; market-neutral, deflated, OOS).")


if __name__ == "__main__":
    main()
