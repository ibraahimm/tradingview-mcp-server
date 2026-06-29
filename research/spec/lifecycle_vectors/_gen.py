#!/usr/bin/env python3
"""Generate the lifecycle golden-vector ledger (synthetic) + params. Run from repo root:

    python research/spec/lifecycle_vectors/_gen.py

Writes ledger.jsonl + params.json. expected.json is then produced by the LIVE tracker (the source of
truth) via:  node .claude/scripts/saudi-tracker.js stage=conform ledger=<ledger> asof=<asof> > expected.json
so the research Python tracker is conformed against the JS, not the other way round.

The ledger exercises every committed (W1/W2-only) lifecycle state + precedence + badge, as-of 2026-06-29:
  A ACTIVE-W2 (promoted)   B ACTIVE-W1   C FAILED   D GRAD*   E STALE   F EXPIRED
  G FAILED-over-GRAD (precedence)   H ACTIVE-W2 + isNew + nearATH
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ASOF = "2026-06-29"
PARAMS = {"asof": ASOF, "grad_p5y": 2000, "stale_days": 120, "horizon_days": 1826}


def ts(d):
    return int(datetime(*map(int, d.split("-")), tzinfo=timezone.utc).timestamp() * 1000)


def ev(date, source, symbol, name, close, fclose, fseen, bath, off, p5y, vs200):
    return {"date": date, "ts": ts(date), "source": source, "symbol": symbol, "name": name,
            "close": close, "first_close": fclose, "first_seen": fseen, "first_source": "W1",
            "belowATH": bath, "offLow": off, "Perf.5Y": p5y, "vs200": vs200}


EVENTS = [
    # A — ACTIVE-W2, promoted (W1 then W2), not new
    ev("2026-05-01", "W1", "TADAWUL:A", "Alpha", 10.0, 10.0, "2026-05-01", 50, 25, 80, None),
    ev("2026-06-15", "W2", "TADAWUL:A", "Alpha", 12.0, 10.0, "2026-05-01", 40, 60, 80, 5.0),
    # B — ACTIVE-W1 (never reached W2, no EMA -> cannot be FAILED)
    ev("2026-06-20", "W1", "TADAWUL:B", "Bravo", 5.0, 5.0, "2026-06-20", 70, 30, None, None),
    # C — FAILED (close < first_close AND vs200 < 0)
    ev("2025-01-10", "W1", "TADAWUL:C", "Charlie", 20.0, 20.0, "2025-01-10", 60, 25, 10, None),
    ev("2025-03-01", "W2", "TADAWUL:C", "Charlie", 15.0, 20.0, "2025-01-10", 65, 10, 10, -8.0),
    # D — GRAD* (Perf.5Y > 2000)
    ev("2024-02-01", "W2", "TADAWUL:D", "Delta", 55.0, 50.0, "2024-02-01", 30, 80, 2500, 12.0),
    # E — STALE (last seen > 120d ago, age < horizon, not failed/grad)
    ev("2025-01-01", "W1", "TADAWUL:E", "Echo", 8.0, 8.0, "2025-01-01", 75, 22, 50, None),
    # F — EXPIRED (age since first_seen > 1826d)
    ev("2019-01-01", "W1", "TADAWUL:F", "Foxtrot", 30.0, 30.0, "2019-01-01", 80, 20, 100, None),
    ev("2019-06-01", "W2", "TADAWUL:F", "Foxtrot", 33.0, 30.0, "2019-01-01", 70, 30, 100, 6.0),
    # G — FAILED takes precedence over GRAD* (both true)
    ev("2024-05-01", "W1", "TADAWUL:G", "Golf", 25.0, 25.0, "2024-05-01", 45, 40, 3000, None),
    ev("2024-06-01", "W2", "TADAWUL:G", "Golf", 18.0, 25.0, "2024-05-01", 40, 50, 3000, -4.0),
    # H — ACTIVE-W2 + isNew (first_seen == latest run) + nearATH (belowATH < 10)
    ev("2026-06-29", "W2", "TADAWUL:H", "Hotel", 100.0, 100.0, "2026-06-29", 5, 90, 150, 8.0),
]


def main():
    with open(os.path.join(HERE, "ledger.jsonl"), "w") as f:
        for e in EVENTS:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(HERE, "params.json"), "w") as f:
        json.dump(PARAMS, f, indent=2)
    print(f"wrote ledger.jsonl ({len(EVENTS)} events) + params.json (asof {ASOF})")


if __name__ == "__main__":
    main()
