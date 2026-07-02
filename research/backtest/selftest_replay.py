"""Self-test for the historical event-generation layer (the tracker it feeds is already proven).

    python -m research.backtest.selftest_replay
"""
from __future__ import annotations
from datetime import date

import polars as pl

from .replay import generate_ledger, journey_outcomes

FAILS = []


def check(c, m):
    if not c:
        FAILS.append(m)


def _frame(rows):
    return pl.DataFrame(rows, schema={"sec_id": pl.Utf8, "date": pl.Date, "close": pl.Float64,
                                      "below_ath": pl.Float64, "off_low": pl.Float64, "vs200": pl.Float64,
                                      "perf_5y": pl.Float64, "passed": pl.Boolean})


def main() -> int:
    # X: TASI-W1 on two days (close 10 then 11), then TASI-W2 later (close 12, vs200>0) -> promoted, journey TASI-W1->TASI-W2
    w1 = _frame([
        {"sec_id": "X", "date": date(2020, 1, 1), "close": 10.0, "below_ath": 60.0, "off_low": 30.0, "vs200": -1.0, "perf_5y": 50.0, "passed": True},
        {"sec_id": "X", "date": date(2020, 2, 1), "close": 11.0, "below_ath": 55.0, "off_low": 40.0, "vs200": 1.0, "perf_5y": 50.0, "passed": True},
        {"sec_id": "Z", "date": date(2020, 1, 1), "close": 5.0, "below_ath": 70.0, "off_low": 25.0, "vs200": None, "perf_5y": 10.0, "passed": False},  # not passed -> excluded
    ])
    w2 = _frame([
        {"sec_id": "X", "date": date(2020, 6, 1), "close": 12.0, "below_ath": 40.0, "off_low": 60.0, "vs200": 5.0, "perf_5y": 50.0, "passed": True},
    ])
    events = generate_ledger({"TASI-W1": w1, "TASI-W2": w2})

    check(len(events) == 3, f"expected 3 events (Z not-passed excluded), got {len(events)}")
    check(all("first_close" in e and "ts" in e and "Perf.5Y" in e for e in events), "event schema incomplete")
    # first_close/first_seen stamped from earliest (close 10 on 2020-01-01)
    check(all(e["first_close"] == 10.0 and e["first_seen"] == "2020-01-01" for e in events),
          "first_close/first_seen must be the earliest event's")
    # daily cadence: two TASI-W1 days -> two TASI-W1 events
    check(sum(e["source"] == "TASI-W1" for e in events) == 2, "expected 2 TASI-W1 events (one per passing day)")

    jr = journey_outcomes(events)
    check(len(jr) == 1, "one journey (X)")
    j = jr[0]
    check(j["entered_w1"] and j["promoted"], "X entered TASI-W1 and promoted to TASI-W2")
    check(j["journey"] == "TASI-W1→TASI-W2", f"journey should be TASI-W1→TASI-W2, got {j['journey']}")
    # max gain = (12/10-1)*100 = 20 ; final gain = 20 (last event is the TASI-W2 at 12)
    check(abs(j["max_gain"] - 20.0) < 1e-9, f"max_gain should be 20, got {j['max_gain']}")
    check(j["terminal"] in ("ACTIVE-TASI-W2", "EXPIRED"), f"terminal should be ACTIVE-TASI-W2/EXPIRED, got {j['terminal']}")

    if FAILS:
        print(f"FAIL ({len(FAILS)}):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: replay self-test OK (event schema, cadence, first-stamp, journey outcome).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
