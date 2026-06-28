#!/usr/bin/env python3
"""Sequential-lifecycle test: evaluate W1 -> W1->W2 -> W1->W2->W3 as successive filters of ONE
recovery lifecycle, and measure the INCREMENTAL value of each stage.

    python -m research.lifecycle_run research/panel/tadawul_<vintage>.parquet

PRE-REGISTERED (fixed before looking at any result):
  * LINK_K  = 504 trading days (~2 years): max gap linking a stage to the prior one. The recovery
              lifecycle is multi-year, so stages must be allowed to be quarters/years apart.
  * HORIZONS = [20, 60, 120, 252, 504]: longer than the standalone passes — "did the recovery
              succeed" is a multi-quarter/multi-year question.
  * Inference: cluster-robust block bootstrap; stage-vs-stage improvement = P(mean_later > mean_earlier).

Two views (see research/backtest/lifecycle.py):
  TRADEABLE  — enter at each stage's own trigger, prior stage required in the PAST (no look-ahead).
  DIAGNOSTIC — split the W1 entries by whether they LATER progress to W2/W3 (uses the future on
               purpose; answers "does the transition separate failed from successful recoveries").
"""
from __future__ import annotations
import os
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load, _load_terminals, CUT                    # noqa: E402
from research.engine.panel import build_panel                              # noqa: E402
from research.engine.screen import compute_age_years, compute_value        # noqa: E402
from research.engine import rules as R                                      # noqa: E402
from research.backtest.event_study import label_forward_returns            # noqa: E402
from research.backtest.rigor import add_excess, with_td_idx, dedup_signals  # noqa: E402
from research.backtest.robust import block_bootstrap, prob_greater         # noqa: E402
from research.backtest.lifecycle import mark_stages                        # noqa: E402

LINK_K = 504
HORIZONS = [20, 60, 120, 252, 504]
B = 5000


def f(x, d=2):
    return "  n/a" if x is None else f"{x:+.{d}f}"


def kept_for(marked, col, h):
    return dedup_signals(marked, h, signal_col=col)


def stats(kept, h):
    dts = kept.get_column("date").to_list()
    ab = block_bootstrap(dts, kept.get_column(f"fwd_{h}").to_list(), n_boot=B, seed=0)
    se = block_bootstrap(dts, kept.get_column(f"xs_{h}").to_list(), n_boot=B, seed=0)
    fv = [v for v in kept.get_column(f"fwd_{h}").to_list() if v is not None]
    hit = (sum(1 for v in fv if v > 0) / len(fv) * 100) if fv else None
    return ab, se, hit


def main():
    prices = load(sys.argv[1])
    sm = prices.group_by("sec_id").agg(
        pl.col("date").min().alias("list_date"), pl.col("date").max().alias("last_date")
    ).with_columns(delist_date=pl.when(pl.col("last_date") < CUT).then(pl.col("last_date")).otherwise(None))
    tv = _load_terminals()
    sm = sm.join(pl.DataFrame({"sec_id": list(tv), "terminal_value": list(tv.values())},
                              schema={"sec_id": pl.Utf8, "terminal_value": pl.Float64}), on="sec_id", how="left")

    print(f"loaded {prices.height:,} rows / {prices['sec_id'].n_unique()} secs; "
          f"building panel (link K={LINK_K} td, horizons={HORIZONS}) ...")
    panel = build_panel(prices)
    labeled = with_td_idx(add_excess(
        label_forward_returns(compute_value(compute_age_years(panel, sm)), sm, horizons=HORIZONS), HORIZONS))
    rules = R.load_rules()
    dW1 = R.evaluate_frame(rules["W1"], labeled, None)
    dW2 = R.evaluate_frame(rules["W2"], labeled, None)
    dW3 = R.evaluate_frame(rules["W3"], labeled, None)
    marked = mark_stages(labeled, dW1, dW2, dW3, LINK_K)

    raw = {c: marked.get_column(c).sum() for c in ("stg_w1", "stg_w2", "stg_w3", "w1_conf2", "w1_conf3")}
    print(f"\nraw triggers (pre-dedup): W1={raw['stg_w1']}  W1->W2(linked)={raw['stg_w2']}  "
          f"W1->W2->W3(linked)={raw['stg_w3']}")
    print(f"of {raw['stg_w1']} W1 bars: {raw['w1_conf2']} later reach W2, {raw['w1_conf3']} reach W3 "
          f"(diagnostic; within {LINK_K} td)")

    # ---------------- TRADEABLE funnel: enter at each stage's own trigger (look-ahead-free) ----------------
    stages = [("W1", "stg_w1"), ("W1->W2", "stg_w2"), ("W1->W2->W3", "stg_w3")]
    print(f"\n{'='*92}\nTRADEABLE — forward return entered at each stage's trigger; "
          f"step-up P = P(this stage's absolute > previous stage's)\n{'='*92}")
    print(f"{'H':>4} {'stage':12} {'n':>5}  {'abs%(p)':>15} {'hit%':>5}  {'sel%(p)':>15}  {'step-up P(abs>prev)':>20}")
    for h in HORIZONS:
        prev = None
        for name, col in stages:
            kept = kept_for(marked, col, h)
            if kept.height == 0:
                print(f"{h:>4} {name:12} {0:>5}  {'(none)':>15}")
                prev = None
                continue
            ab, se, hit = stats(kept, h)
            step = ""
            if prev is not None and prev.height > 0:
                p = prob_greater(kept.get_column("date").to_list(), kept.get_column(f"fwd_{h}").to_list(),
                                 prev.get_column("date").to_list(), prev.get_column(f"fwd_{h}").to_list(),
                                 n_boot=B, seed=0)
                dlt = ab["mean"] - block_bootstrap(prev.get_column("date").to_list(),
                                                   prev.get_column(f"fwd_{h}").to_list(), n_boot=1, seed=0)["mean"]
                step = f"{f(p,2)} (d{f(dlt,1)})"
            print(f"{h:>4} {name:12} {ab['n']:>5}  {f(ab['mean']):>7}({f(ab['p_boot'],3)}) {f(hit,0):>5}  "
                  f"{f(se['mean']):>7}({f(se['p_boot'],3)})  {step:>20}")
            prev = kept
        print()

    # ---------------- DIAGNOSTIC: do W1 entries that LATER progress fare better? (uses future) ----------------
    marked = marked.with_columns(
        g_fail=(pl.col("stg_w1") & ~pl.col("w1_conf2")),
        g_w2only=(pl.col("stg_w1") & pl.col("w1_conf2") & ~pl.col("w1_conf3")),
        g_w3=(pl.col("stg_w1") & pl.col("w1_conf3")),
        g_conf2=(pl.col("stg_w1") & pl.col("w1_conf2")),
    )
    print(f"{'='*92}\nDIAGNOSTIC — W1 entries split by whether the lifecycle LATER progresses (uses future, "
          f"NOT tradeable)\n  does confirming W2/W3 separate successful recoveries from failed ones?\n{'='*92}")
    print(f"{'H':>4} {'W1 group':12} {'n':>5}  {'abs%(p)':>15} {'hit%':>5}     "
          f"conf-W2 vs fail: P(better), d-abs")
    for h in (120, 252, 504):
        sub = {}
        for name, col in (("fail-W2", "g_fail"), ("conf-W2only", "g_w2only"), ("conf-W3", "g_w3"),
                          ("[conf-W2 all]", "g_conf2")):
            kept = kept_for(marked, col, h)
            sub[col] = kept
            if kept.height == 0:
                print(f"{h:>4} {name:12} {0:>5}  {'(none)':>15}")
                continue
            ab, _, hit = stats(kept, h)
            extra = ""
            if col == "g_conf2" and sub.get("g_fail") is not None and sub["g_fail"].height > 0:
                p = prob_greater(kept.get_column("date").to_list(), kept.get_column(f"fwd_{h}").to_list(),
                                 sub["g_fail"].get_column("date").to_list(),
                                 sub["g_fail"].get_column(f"fwd_{h}").to_list(), n_boot=B, seed=0)
                fab = block_bootstrap(sub["g_fail"].get_column("date").to_list(),
                                      sub["g_fail"].get_column(f"fwd_{h}").to_list(), n_boot=1, seed=0)["mean"]
                extra = f"   P={f(p,2)}, d={f(ab['mean']-fab,1)}"
            print(f"{h:>4} {name:12} {ab['n']:>5}  {f(ab['mean']):>7}({f(ab['p_boot'],3)}) {f(hit,0):>5}{extra}")
        print()

    print("Reading: TRADEABLE step-up P>~0.6 => entering at the later stage is genuinely better timing. "
          "DIAGNOSTIC conf-W2>fail (P>~0.6) => the W2 transition really does pick the W1 entries that worked.")
    print("DONE.")


if __name__ == "__main__":
    main()
