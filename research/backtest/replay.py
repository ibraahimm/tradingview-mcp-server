"""Historical event-GENERATION + replay of the documented TASI-W1/TASI-W2 tracker methodology.

Faithfulness split (see research/spec/lifecycle.md §4):
  * The tracker STATE MACHINE is unchanged — we reuse research.backtest.tracker (proven == live JS).
  * This module is the EVENT-GENERATION layer, where the documented live-vs-backtest adaptations live:
      A2 cadence : every trading day a wave's gate passes => one event ("screen run every day"); the live
                   ledger is a sparse human-driven sample of this.
      A3 STALE   : becomes gate-driven (the setup stopped qualifying) not usage-driven.
      A4 first_seen: first trading day the gate passes (deterministic), matching the live ingest stamping.
      vs200      : stamped on TASI-W1 events too — faithful to the CURRENT committed saudi-stage2 (which fetches
                   EMA200 as a descriptor so TASI-W1-only names can be FAILED). Not a research change.
  * `name` = sec_id (the panel carries no company name) — cosmetic only.

This replays the documented methodology through history; it is NOT a new research strategy. Any
forward-looking outcome (returns after a journey ends) would be a research adaptation and is kept OUT.
"""
from __future__ import annotations
from datetime import datetime, timezone

import polars as pl

from .tracker import build_items, ts, GRAD_P5Y, STALE_DAYS, HORIZON_DAYS

_EV_COLS = ["sec_id", "date", "close", "below_ath", "off_low", "vs200", "perf_5y"]


def _ms(d) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def generate_ledger(decided_by_source: dict) -> list:
    """Turn engine pass-rows into ledger events (live schema). `decided_by_source` = {"TASI-W1": frame,
    "TASI-W2": frame} where each frame has `passed` + the feature columns. Daily cadence (A2): one event per
    passing bar. first_close/first_seen stamped from the earliest event per symbol (A4)."""
    frames = []
    for source, d in decided_by_source.items():
        frames.append(d.filter(pl.col("passed")).select(_EV_COLS).with_columns(pl.lit(source).alias("source")))
    allp = pl.concat(frames).sort(["sec_id", "date"])

    events = []
    for r in allp.iter_rows(named=True):
        d = r["date"]
        events.append({
            "date": d.isoformat(), "ts": _ms(d), "source": r["source"], "symbol": r["sec_id"],
            "name": r["sec_id"],
            "close": round(r["close"], 2) if r["close"] is not None else None,
            "belowATH": round(r["below_ath"], 1) if r["below_ath"] is not None else None,
            "offLow": round(r["off_low"], 1) if r["off_low"] is not None else None,
            "vs200": r["vs200"], "Perf.5Y": r["perf_5y"],
        })
    # stamp journey origin (earliest event per symbol) — mirrors saudi-tracker.js ingest
    first = {}
    for e in events:  # events are already (sec_id, date)-sorted
        f = first.get(e["symbol"])
        if f is None:
            first[e["symbol"]] = f = {"fc": e["close"], "fs": e["date"], "src": e["source"]}
        e["first_close"], e["first_seen"], e["first_source"] = f["fc"], f["fs"], f["src"]
    return events


def journey_outcomes(events: list, grad_p5y=GRAD_P5Y, stale_days=STALE_DAYS, horizon_days=HORIZON_DAYS):
    """Per-symbol faithful tracker journey outcome. Terminal state is classified at as_of = the
    journey's LAST event date (so STALE/age reflect when it stopped qualifying). gainSinceSignal is the
    tracker's own metric across the journey's event closes (max + final). No forward look."""
    by_sym: dict = {}
    for e in events:
        by_sym.setdefault(e["symbol"], []).append(e)
    rows = []
    for sym, evs in by_sym.items():
        evs = sorted(evs, key=lambda x: x["ts"])
        fc = evs[0]["first_close"]
        gains = [((e["close"] / fc - 1) * 100) if fc else None for e in evs]
        gains = [g for g in gains if g is not None]
        last_date = evs[-1]["date"]
        items, _ = build_items(evs, ts(last_date), grad_p5y, stale_days, horizon_days)
        it = items[0]
        rows.append({
            "symbol": sym, "n_events": len(evs),
            "entered_w1": any(e["source"] == "TASI-W1" for e in evs),
            "promoted": it["promoted"], "journey": it["journey"], "terminal": it["state"],
            "first_seen": evs[0]["first_seen"], "last_seen": last_date,
            "max_gain": max(gains) if gains else None, "final_gain": gains[-1] if gains else None,
        })
    return rows
