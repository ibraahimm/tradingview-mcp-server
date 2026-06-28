"""Self-test for the rigor layer (runnable gate; exits non-zero on failure).

Hand-computed: non-overlapping dedup (spacing >= horizon in trading days) and market-neutral
excess (signal minus the cross-sectional date mean).

    python -m research.backtest.selftest_rigor
"""
from __future__ import annotations
from datetime import date

import polars as pl

from .rigor import dedup_signals, add_excess, study

FAILS = []


def check(c, m):
    if not c:
        FAILS.append(m)


def main() -> int:
    # 1. dedup: one sec, passed at td_idx 0,1,2,5,9; horizon=3 -> keep {0,5,9}
    df = pl.DataFrame({
        "sec_id": ["A"] * 11,
        "td_idx": list(range(11)),
        "passed": [i in (0, 1, 2, 5, 9) for i in range(11)],
    })
    kept = dedup_signals(df, horizon=3)
    got = sorted(kept.get_column("td_idx").to_list())
    check(got == [0, 5, 9], f"dedup horizon=3 should keep [0,5,9], got {got}")
    # horizon=1 keeps all passed (every signal >=1 apart)
    check(sorted(dedup_signals(df, 1).get_column("td_idx").to_list()) == [0, 1, 2, 5, 9], "dedup h=1 wrong")
    # two names independent
    df2 = pl.DataFrame({"sec_id": ["A", "A", "B"], "td_idx": [0, 1, 1], "passed": [True, True, True]})
    check(dedup_signals(df2, 3).height == 2, "dedup must be per-security (A:1 kept + B:1 kept = 2)")

    # 2. excess: two names on the same date, fwd 10 and 20 -> date-mean 15 -> xs -5 / +5
    lab = pl.DataFrame({
        "sec_id": ["A", "B", "A", "B"],
        "date": [date(2020, 1, 1), date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 2)],
        "fwd_60": [10.0, 20.0, 4.0, 8.0],
    })
    xs = add_excess(lab, [60]).sort(["date", "sec_id"])
    vals = xs.get_column("xs_60").to_list()
    check(vals == [-5.0, 5.0, -2.0, 2.0], f"excess wrong: {vals}")

    # 3. study integrates dedup + excess: one sec, daily signals, horizon spaces them out
    dec = add_excess(
        pl.DataFrame({
            "sec_id": ["A"] * 6,
            "date": [date(2020, 1, d) for d in range(1, 7)],
            "td_idx": list(range(6)),
            "passed": [True] * 6,
            "fwd_20": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        }), [20])
    st = study(dec, 20, excess=True)
    check(st["raw_signals"] == 6, "study raw_signals should be 6")
    check(st["independent"] == 1, f"study should dedup 6 daily signals to 1 at horizon=20, got {st['independent']}")

    if FAILS:
        print(f"FAIL ({len(FAILS)}):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: rigor self-test OK (dedup non-overlap + market-neutral excess + study).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
