"""Self-test for the screen run (runnable gate; exits non-zero on failure).

Proves the new wiring with hand-computed expectations: age_years computation + gating, value
(trailing ADV) computation + warmup null + gating, the funnel, and the survivor set.

    python -m research.engine.selftest_screen
"""
from __future__ import annotations
from datetime import date

import polars as pl

from .screen import run_screen

FAILS: list[str] = []


def check(cond: bool, msg: str):
    if not cond:
        FAILS.append(msg)


# Baseline W1-passing price features (from the w1_defaults 'P' fixture).
BASE = dict(perf_3m=17.0, perf_6m=29.0, perf_3y=-20.0, perf_5y=-25.0, perf_10y=-8.0,
            ddmax=77.0, below_ath=68.0, off_low=39.0, ext60=7.6, nrhi=98.0)
DATES = [date(2020, 1, d) for d in (1, 2, 3, 4, 5)]


def _frame():
    rows = []
    aaa_vol = [100, 100, 100, 200, 200]
    for i, dt in enumerate(DATES):
        r = dict(sec_id="AAA", date=dt, close=10.0, volume=aaa_vol[i], **BASE)
        if i == 3:
            r["ext60"] = 20.0          # bar3: high ext60 — no longer gated (extension cap removed 2026-06-30)
        rows.append(r)
    for dt in DATES:                    # BBB: same features, but listed only days ago -> fails age
        rows.append(dict(sec_id="BBB", date=dt, close=10.0, volume=100, **BASE))
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


def main() -> int:
    prices = _frame()
    sm = pl.DataFrame({
        "sec_id": ["AAA", "BBB"],
        "list_date": [date(2014, 1, 1), date(2019, 12, 30)],
    }).with_columns(pl.col("list_date").cast(pl.Date))

    # ---- Run 1: default W1 (value gate disabled: value_min=0) ----
    surv, funnel, decided = run_screen(prices, sm, "W1", value_window=3)
    d = {(r["sec_id"], r["date"]): r for r in decided.iter_rows(named=True)}

    # age_years computation + gating
    check(d[("BBB", DATES[0])]["age_years"] < 5, "BBB age_years should be < 5")
    for dt in DATES:
        check(d[("BBB", dt)]["first_fail"] == "age_years", f"BBB {dt} should fail at age_years")
    check(d[("AAA", DATES[0])]["age_years"] > 5.99, "AAA age_years should be ~6")

    # value (trailing ADV) computation: window=3 -> bars 0,1 null; bar2=1000; bar4≈1666.667
    check(d[("AAA", DATES[0])]["value"] is None and d[("AAA", DATES[1])]["value"] is None,
          "AAA value should be null during the 3-bar warmup")
    check(abs(d[("AAA", DATES[2])]["value"] - 1000.0) < 1e-9, "AAA bar2 value should be 1000")
    check(abs(d[("AAA", DATES[4])]["value"] - 5000.0 / 3) < 1e-9, "AAA bar4 value should be 1666.667")

    # funnel + survivors
    fbase = funnel[0][1]
    after_age = funnel[1][1]
    final = funnel[-1][1]
    check(fbase == 10, f"funnel base should be 10, got {fbase}")
    check(after_age == 5, f"after age_years should be 5 (BBB dropped), got {after_age}")
    check(final == 5, f"final survivors should be 5 (all AAA bars; ext60 no longer gates), got {final}")
    check(surv.height == 5 and final == surv.height, "survivors must equal final funnel count")
    check(set(surv.get_column("sec_id").to_list()) == {"AAA"}, "only AAA should survive")
    surv_dates = set(surv.get_column("date").to_list())
    check(surv_dates == set(DATES),
          f"AAA survivors should be all 5 bars (ext60 cap removed), got {sorted(surv_dates)}")
    check(d[("AAA", DATES[3])]["passed"] is True, "AAA bar3 (ext60=20) should now PASS (extension cap removed)")
    # funnel monotonic non-increasing
    counts = [c for _, c in funnel]
    check(all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)), "funnel not monotonic")

    # ---- Run 2: enable the value floor (value_min=1200) -> computed value participates ----
    surv2, _, decided2 = run_screen(prices, sm, "W1", params_overrides={"value_min": 1200}, value_window=3)
    d2 = {(r["sec_id"], r["date"]): r for r in decided2.iter_rows(named=True)}
    check(surv2.height == 2, f"with value_min=1200 AAA bars 3,4 survive (value>=1200), got {surv2.height}")
    check(d2[("AAA", DATES[4])]["passed"] is True, "AAA bar4 (value 1666.7) should pass value floor")
    check(d2[("AAA", DATES[3])]["passed"] is True, "AAA bar3 (value 1333.3) should pass (ext60 no longer gates)")
    check(d2[("AAA", DATES[2])]["first_fail"] == "value", "AAA bar2 (value 1000<1200) should fail at value")
    check(d2[("AAA", DATES[0])]["first_fail"] == "value", "AAA bar0 (value null) should drop at value")

    if FAILS:
        print(f"FAIL ({len(FAILS)} issue(s)):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: screen-run self-test OK (age_years + value + funnel + survivors, 2 runs).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
