"""Self-test for the market-regime layer (runnable gate; exits non-zero on failure).

    python -m research.backtest.selftest_regime
"""
from __future__ import annotations
from datetime import date, timedelta

import polars as pl

from .regime import (build_market, market_forward, assign_regimes, episode_of, EPISODE_NAMES)

FAILS = []


def check(c, m):
    if not c:
        FAILS.append(m)


def synth_prices() -> pl.DataFrame:
    """One name whose close rises 100->200 (peak), falls to 130 (=35% off the peak), recovers to 250
    (new high). Daily steps are <30% so the clip is inert and mkt_level == close/close[0] exactly."""
    closes = (list(range(100, 201, 2))          # 100 -> 200  (up leg, peak = 200)
              + list(range(198, 129, -2))        # 200 -> 130  (crash, trough = 130 => dd 0.35)
              + list(range(132, 251, 2)))        # 130 -> 250  (recovery to a new high)
    d0 = date(2008, 1, 1)
    rows = [{"date": d0 + timedelta(days=i), "sec_id": "A", "close": float(c)}
            for i, c in enumerate(closes)]
    return pl.DataFrame(rows)


def main() -> int:
    px = synth_prices()
    mk = assign_regimes(market_forward(build_market(px, roll_win=252), horizons=[10]))

    # mkt_level tracks close/close[0] (clip inert). The PRE-CRASH local peak is the bar where
    # close==200 -> level 2.0 (NOT the global max, which is the later new high at 250).
    peak_date = px.filter(pl.col("close") == 200.0).get_column("date")[0]
    peak_row = mk.filter(pl.col("date") == peak_date)
    check(abs(peak_row.get_column("mkt_level")[0] - 2.0) < 1e-6,
          f"pre-crash peak level should be 2.0, got {peak_row.get_column('mkt_level')[0]}")

    # drawdown: max dd == 0.35 at the trough; reg_dd35 (and reg_dd20) fire there, reg_normal off
    trough = mk.filter(pl.col("dd") == pl.col("dd").max())
    max_dd = trough.get_column("dd")[0]
    check(abs(max_dd - 0.35) < 1e-6, f"max drawdown should be 0.35, got {max_dd}")
    check(bool(trough.get_column("reg_dd35")[0]) and bool(trough.get_column("reg_dd20")[0]),
          "trough must be in reg_dd35 and reg_dd20")
    check(not bool(trough.get_column("reg_normal")[0]), "trough must NOT be reg_normal")

    # CAUSALITY / no look-ahead: at the pre-crash PEAK bar dd==0 even though a 35% crash follows next.
    check(abs(peak_row.get_column("dd")[0]) < 1e-9, "dd at the peak must be 0 (no look-ahead into the crash)")

    # new-high recovery: final bar dd back to ~0
    check(abs(mk.get_column("dd")[-1]) < 1e-9, "dd at the final new high should be ~0")

    # market_forward: 10-day-ahead return at the peak is negative (the crash that follows)
    peak_fwd = peak_row.get_column("mkt_fwd_10")[0]
    check(peak_fwd is not None and peak_fwd < 0, f"mkt_fwd_10 at peak should be negative, got {peak_fwd}")
    check(mk.get_column("mkt_fwd_10")[-1] is None, "mkt_fwd_10 must be right-censored (null) at the tail")

    # below_ema200: early ramp sits above its own EMA (level rising) -> not below
    check(not bool(mk.get_column("below_ema200")[5]), "rising early ramp should be above EMA200")

    # episode mapping (fixed windows)
    check(episode_of(date(2008, 10, 1)) == "2008", "2008-10 should map to 2008 episode")
    check(episode_of(date(2020, 3, 15)) == "2020", "2020-03 should map to 2020 episode")
    check(episode_of(date(2012, 6, 1)) == "other", "2012 (calm) should map to 'other'")
    check(set(EPISODE_NAMES) == {"2006", "2008", "2014-15", "2020"}, "episode set drifted")

    # determinism: pure transform reproduces bit-for-bit
    mk2 = assign_regimes(market_forward(build_market(px, roll_win=252), horizons=[10]))
    check(mk.equals(mk2), "build_market must be deterministic")

    if FAILS:
        print(f"FAIL ({len(FAILS)}):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: regime self-test OK (drawdown depth + regime flags + causality + forward + episodes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
