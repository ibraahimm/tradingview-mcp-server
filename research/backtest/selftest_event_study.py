"""Self-test for the event-study core (runnable gate; exits non-zero on failure).

Hand-computed forward-return labels on a controlled 2-security panel: a still-listed name (tail
right-censored -> null) and a DELISTED name (tail realizes terminal_value, not last price), plus
the aggregates and the signals-vs-rest split.

    python -m research.backtest.selftest_event_study
"""
from __future__ import annotations
from datetime import date

import polars as pl

from .event_study import label_forward_returns, aggregate, event_study

FAILS: list[str] = []


def check(cond: bool, msg: str):
    if not cond:
        FAILS.append(msg)


def approx(a, b, tol=1e-6):
    return a is not None and abs(a - b) < tol


def main() -> int:
    # LIVE: still listed, closes 10..15. GONE: delisted, closes 20,18,16,14, terminal_value 5.
    def bars(sec, closes, d0=date(2021, 1, 1)):
        return [{"sec_id": sec, "date": date(2021, 1, 1 + i), "close": float(c)}
                for i, c in enumerate(closes)]
    panel = pl.DataFrame(bars("LIVE", [10, 11, 12, 13, 14, 15]) + bars("GONE", [20, 18, 16, 14])) \
        .with_columns(pl.col("date").cast(pl.Date))
    sm = pl.DataFrame({
        "sec_id": ["LIVE", "GONE"],
        "delist_date": [None, date(2021, 1, 5)],
        "terminal_value": [None, 5.0],
    }).with_columns(pl.col("delist_date").cast(pl.Date))

    lab = label_forward_returns(panel, sm, horizons=[2])
    d = {(r["sec_id"], r["date"].day): r["fwd_2"] for r in lab.iter_rows(named=True)}

    # LIVE: normal forward returns; last 2 bars right-censored -> null
    check(approx(d[("LIVE", 1)], 20.0), "LIVE day1 fwd_2 should be 20%")
    check(approx(d[("LIVE", 2)], 13 / 11 * 100 - 100), "LIVE day2 fwd_2 wrong")
    check(approx(d[("LIVE", 3)], 14 / 12 * 100 - 100), "LIVE day3 fwd_2 wrong")
    check(approx(d[("LIVE", 4)], 15 / 13 * 100 - 100), "LIVE day4 fwd_2 wrong")
    check(d[("LIVE", 5)] is None and d[("LIVE", 6)] is None, "LIVE tail should be null (right-censored)")

    # GONE: normal where a bar exists; tail realizes terminal_value 5 (NOT last price)
    check(approx(d[("GONE", 1)], -20.0), "GONE day1 fwd_2 should be -20%")
    check(approx(d[("GONE", 2)], 14 / 18 * 100 - 100), "GONE day2 fwd_2 wrong")
    check(approx(d[("GONE", 3)], 5 / 16 * 100 - 100), "GONE day3 should realize terminal (5/16-1)")
    check(approx(d[("GONE", 4)], 5 / 14 * 100 - 100), "GONE day4 should realize terminal (5/14-1)")

    # aggregates over all non-null fwd_2 (4 LIVE positives + 4 GONE negatives)
    agg = aggregate(lab, 2)
    check(agg["n"] == 8, f"n should be 8, got {agg['n']}")
    check(approx(agg["hit_rate"], 50.0), f"hit_rate should be 50, got {agg['hit_rate']}")
    # median = mean of the 4th/5th sorted values = (-20 + 15.3846)/2
    check(approx(agg["median"], (-20.0 + (15 / 13 * 100 - 100)) / 2, 1e-6), "median wrong")

    # signals-vs-rest A/B using a mask: LIVE rows as "signals"
    lab2 = lab.with_columns(passed=pl.col("sec_id") == "LIVE")
    ab = event_study(lab2, 2, "passed")
    check(ab["signals"]["n"] == 4 and approx(ab["signals"]["hit_rate"], 100.0),
          "LIVE signals should be n=4, hit_rate=100")
    check(ab["rest"]["n"] == 4 and approx(ab["rest"]["hit_rate"], 0.0),
          "GONE rest should be n=4, hit_rate=0")
    check(ab["signals"]["mean"] > ab["rest"]["mean"], "signals mean should exceed rest mean")

    if FAILS:
        print(f"FAIL ({len(FAILS)} issue(s)):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: event-study self-test OK (labels incl. terminal-value + censoring, aggregates, A/B).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
