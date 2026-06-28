#!/usr/bin/env python3
"""Conditional regime test: does the W1/W2 edge live specifically in market crisis / deep-drawdown
environments, and is it stock-SELECTION skill or market-TIMING/recovery (beta) exposure?

    python -m research.regime_run research/panel/tadawul_<vintage>.parquet

Two readings, both reported, per the agreed design:
  (A) SELECTION  = market-neutral excess xs_<h> (name minus its same-date cohort). Removes the market's
      recovery move -> isolates "did the corrected names beat their peers."
  (B) TIMING     = absolute forward return fwd_<h>. Includes the market bounce -> "did buying corrected
      names in a crashed market pay, mostly via the recovery." (mkt_fwd_<h> shows how much is just beta.)

Regimes are PRE-REGISTERED in research/backtest/regime.py (dd>=20%, dd>=35%, below-EMA200; trailing-1y
drawdown to dodge the 2006-bubble ATH overhang). Inference is the same cluster-robust block bootstrap.
Leave-one-crisis-out (2006/2008/2014-15/2020) tests whether any result is stable or one-crisis-driven.
"""
from __future__ import annotations
import os
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load, _load_terminals, CUT                         # noqa: E402
from research.engine.panel import build_panel                                    # noqa: E402
from research.engine.screen import compute_age_years, compute_value             # noqa: E402
from research.engine import rules as R                                           # noqa: E402
from research.backtest.event_study import label_forward_returns                  # noqa: E402
from research.backtest.rigor import add_excess, with_td_idx, dedup_signals       # noqa: E402
from research.backtest.robust import block_bootstrap                             # noqa: E402
from research.backtest import regime as RG                                       # noqa: E402

HORIZONS = [20, 60, 120]
BUCKETS = [("dd>=20%", "reg_dd20"), ("dd>=35%", "reg_dd35"),
           ("below200", "reg_below200"), ("normal", "reg_normal")]
B = 5000
SIG = 0.05


def f(x, d=2):
    return "  n/a" if x is None else f"{x:+.{d}f}"


def verdict(A: dict, Bb: dict) -> str:
    a = A["mean"] is not None and A["p_boot"] is not None and A["p_boot"] < SIG and A["ci_low"] > 0
    b = Bb["mean"] is not None and Bb["p_boot"] is not None and Bb["p_boot"] < SIG and Bb["ci_low"] > 0
    if a and b:
        return "SELECTION(+timing)"
    if a:
        return "SELECTION"
    if b:
        return "TIMING/recovery"
    return "neither"


def boot(sub, col):
    return block_bootstrap(sub.get_column("date").to_list(),
                           sub.get_column(col).to_list(), n_boot=B, seed=0)


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(
        pl.col("date").min().alias("list_date"), pl.col("date").max().alias("last_date")
    ).with_columns(delist_date=pl.when(pl.col("last_date") < CUT).then(pl.col("last_date")).otherwise(None))
    tv = _load_terminals()
    sm = sm.join(pl.DataFrame({"sec_id": list(tv), "terminal_value": list(tv.values())},
                              schema={"sec_id": pl.Utf8, "terminal_value": pl.Float64}), on="sec_id", how="left")

    print(f"loaded {prices.height:,} rows / {prices['sec_id'].n_unique()} secs; building market proxy + panel ...")
    mkt = RG.market_table(prices, HORIZONS)               # per-date regime flags + mkt_fwd_<h>
    reg_cols = ["date"] + RG.REGIME_COLS + [f"mkt_fwd_{h}" for h in HORIZONS]
    mkt_join = mkt.select(reg_cols)

    panel = build_panel(prices)
    labeled = with_td_idx(add_excess(
        label_forward_returns(compute_value(compute_age_years(panel, sm)), sm, horizons=HORIZONS), HORIZONS))

    # regime coverage (context): share of trading days in each regime
    nday = mkt.height
    cov = {name: mkt.get_column(col).sum() for name, col in BUCKETS}
    print(f"\nregime coverage over {nday:,} market days: " +
          ", ".join(f"{n} {c}/{nday} ({100*c/nday:.0f}%)" for (n, _), c in zip(BUCKETS, cov.values())))

    rules = R.load_rules()
    for rule in ("W1", "W2"):
        decided = R.evaluate_frame(rules[rule], labeled, None)
        print(f"\n{'='*94}\n{rule}: conditional regime test "
              f"(B=absolute fwd%, A=selection xs%, mkt=market's own fwd%; boot p in parens)\n{'='*94}")
        print(f"{'regime':10} {'H':>4} {'n':>5}  {'B abs%(p)':>16} {'mkt%':>6}  {'A sel%(p)':>16}  verdict")
        for name, col in BUCKETS:
            for h in HORIZONS:
                kept = dedup_signals(decided, h).join(mkt_join, on="date", how="left")
                sub = kept.filter(pl.col(col))
                if sub.height == 0:
                    print(f"{name:10} {h:>4} {0:>5}  {'(no signals)':>16}")
                    continue
                Bb = boot(sub, f"fwd_{h}")
                A = boot(sub, f"xs_{h}")
                mk = sub.get_column(f"mkt_fwd_{h}").mean()
                print(f"{name:10} {h:>4} {Bb['n']:>5}  {f(Bb['mean']):>7}({f(Bb['p_boot'],3)}) {f(mk):>6}  "
                      f"{f(A['mean']):>7}({f(A['p_boot'],3)})  {verdict(A, Bb)}")

        # Leave-one-crisis-out on the primary crisis bucket (dd>=20%): is any edge stable or 1-crisis-driven?
        print(f"\n-- {rule} leave-one-crisis-out @ dd>=20% (mean only; n in parens). "
              f"Stable = sign holds when each crisis is removed --")
        print(f"{'H':>4} {'metric':6} {'ALL':>12} " + " ".join(f"{'-'+e:>12}" for e in RG.EPISODE_NAMES))
        for h in HORIZONS:
            kept = dedup_signals(decided, h).join(mkt_join, on="date", how="left").filter(pl.col("reg_dd20"))
            if kept.height == 0:
                print(f"{h:>4}  (no dd>=20% signals)")
                continue
            ep = [RG.episode_of(d) for d in kept.get_column("date").to_list()]
            kept = kept.with_columns(pl.Series("ep", ep))
            for metric, mcol in (("B abs", f"fwd_{h}"), ("A sel", f"xs_{h}")):
                cells = []
                allv = kept.get_column(mcol).mean()
                cells.append(f"{f(allv)}({kept.height})")
                for e in RG.EPISODE_NAMES:
                    lo = kept.filter(pl.col("ep") != e)
                    cells.append(f"{f(lo.get_column(mcol).mean())}({lo.height})")
                print(f"{h:>4} {metric:6} " + " ".join(f"{c:>12}" for c in cells))

    print("\nReading: TIMING/recovery = absolute pays but selection (peer-relative) does not -> it's the "
          "market bounce (beta), not skill. SELECTION = beats peers even after removing the market move.")
    print("DONE.")


if __name__ == "__main__":
    main()
