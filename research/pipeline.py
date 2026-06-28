#!/usr/bin/env python3
"""Indicative end-to-end pipeline run over a Saudi Exchange companies directory.

    python -m research.pipeline <companies_dir>

Wires the whole platform on REAL data: load -> build_panel -> enrich (age_years, value) ->
label forward returns -> evaluate W1 over every bar -> event-study (signals vs rest) -> governance
(out-of-sample split). Prints a report.

IMPORTANT: this is ENGINE VALIDATION on RAW/UNADJUSTED prices — not strategy evaluation. Split/
bonus-share discontinuities distort returns until corporate-action adjustment is applied, and
delisted names lack terminal values (right-censored at the tail). Treat every number as indicative.
"""
from __future__ import annotations
import csv
import datetime
import glob
import os
import sys

import polars as pl

TERMINALS = "research/reference/curation/delisted_terminal_values.csv"


def _load_terminals() -> dict:
    if not os.path.exists(TERMINALS):
        return {}
    return {r["sec_id"]: float(r["terminal_value"])
            for r in csv.DictReader(open(TERMINALS, encoding="utf-8-sig"))
            if r.get("terminal_value") not in (None, "")}

sys.path.insert(0, os.getcwd())
from research.engine.panel import build_panel                      # noqa: E402
from research.engine.screen import compute_age_years, compute_value  # noqa: E402
from research.engine import rules as R                              # noqa: E402
from research.backtest.event_study import label_forward_returns, aggregate, event_study  # noqa: E402
from research.backtest import governance as G                       # noqa: E402

CUT = datetime.date(2026, 6, 1)   # last bar before this => delisted/suspended


def load(companies_dir: str) -> pl.DataFrame:
    frames = []
    for f in sorted(glob.glob(os.path.join(companies_dir, "*.csv"))):
        try:
            df = pl.read_csv(f, infer_schema_length=3000, ignore_errors=True)
        except Exception:
            continue
        if not {"date", "open", "high", "low", "close", "volume", "symbol"} <= set(df.columns):
            continue
        df = df.select(
            pl.col("symbol").cast(pl.Utf8).alias("sec_id"),
            pl.col("date").cast(pl.Utf8).str.strptime(pl.Date, "%Y-%m-%d", strict=False).alias("date"),
            pl.col("open").cast(pl.Float64, strict=False),
            pl.col("high").cast(pl.Float64, strict=False),
            pl.col("low").cast(pl.Float64, strict=False),
            pl.col("close").cast(pl.Float64, strict=False),
            pl.col("volume").cast(pl.Float64, strict=False),
        ).drop_nulls(["date", "close", "high", "low"]).filter(pl.col("close") > 0)
        frames.append(df)
    return pl.concat(frames)


def main():
    cdir = sys.argv[1]
    print(">> loading", cdir)
    prices = load(cdir)
    print(f"   {prices.height:,} rows | {prices['sec_id'].n_unique()} securities | "
          f"{prices['date'].min()} -> {prices['date'].max()}")

    sm = prices.group_by("sec_id").agg(
        pl.col("date").min().alias("list_date"), pl.col("date").max().alias("last_date")
    ).with_columns(
        delist_date=pl.when(pl.col("last_date") < CUT).then(pl.col("last_date")).otherwise(None),
    )
    tv = _load_terminals()
    tvdf = pl.DataFrame({"sec_id": list(tv), "terminal_value": list(tv.values())},
                        schema={"sec_id": pl.Utf8, "terminal_value": pl.Float64})
    sm = sm.join(tvdf, on="sec_id", how="left")
    print(f"   delisted/suspended: {sm.filter(pl.col('delist_date').is_not_null()).height} | "
          f"terminal values loaded: {sm.filter(pl.col('terminal_value').is_not_null()).height}")

    print(">> build_panel ...")
    panel = build_panel(prices)
    print(f"   panel: {panel.height:,} rows x {len(panel.columns)} cols")

    print(">> enrich (age_years, value) + label forward returns ...")
    enriched = compute_value(compute_age_years(panel, sm))
    labeled = label_forward_returns(enriched, sm, horizons=[20, 60])

    print(">> evaluate W1 over every bar ...")
    rules = R.load_rules()
    decided = R.evaluate_frame(rules["W1"], labeled)
    nsig = decided.filter(pl.col("passed")).height
    print(f"   W1 signals (passed bars): {nsig:,} of {decided.height:,}")

    latest = decided["date"].max()
    snap = enriched.filter(pl.col("date") == latest)
    fn = R.funnel(rules["W1"], snap)
    print(f">> W1 funnel @ latest {latest} ({snap.height} names): "
          + " -> ".join(f"{s}:{c}" for s, c in fn))

    print(">> event-study (signals vs rest), 60-trading-day forward return:")
    es = event_study(decided, 60, "passed")
    print(f"   signals: {es['signals']}")
    print(f"   rest   : {es['rest']}")

    print(">> governance — out-of-sample split @ 2019-01-01 (signals only):")
    tr, te = G.time_split(decided.filter(pl.col("passed")), datetime.date(2019, 1, 1))
    print(f"   train(<=2018): {aggregate(tr, 60)}")
    print(f"   test (>=2019): {aggregate(te, 60)}")

    print("\nDONE (indicative; raw/unadjusted — engine validation only).")


if __name__ == "__main__":
    main()
