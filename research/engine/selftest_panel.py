"""Self-test for the panel builder (runnable gate; exits non-zero on failure).

Proves the layer rather than documenting it: per-security isolation (no cross-sec leakage),
warmup nulling, ratio null-propagation, and that panel columns equal the gated functions
applied to each security (catches grouping/alignment bugs).

    python -m research.engine.selftest_panel
"""
from __future__ import annotations
from datetime import date, timedelta

import polars as pl

from . import functions as fx
from .panel import build_panel

FAILS: list[str] = []


def check(cond: bool, msg: str):
    if not cond:
        FAILS.append(msg)


def _series(sec, n, base, step, high_spike_at=None, spike=None, start="2020-01-01"):
    d0 = date.fromisoformat(start)
    rows = []
    for i in range(n):
        close = base + step * i
        high = close + 1.0
        low = close - 1.0
        if high_spike_at is not None and i == high_spike_at:
            high = spike
        rows.append({"sec_id": sec, "date": d0 + timedelta(days=i),
                     "high": high, "low": low, "close": float(close)})
    return rows


def main() -> int:
    n = 300
    # AAA rises; carries a one-off extreme HIGH spike at bar 100. BBB is a separate, lower series.
    rows = _series("AAA", n, base=50.0, step=0.10, high_spike_at=100, spike=999.0)
    rows += _series("BBB", n, base=20.0, step=0.05)
    prices = pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))

    panel = build_panel(prices)
    aaa = panel.filter(pl.col("sec_id") == "AAA").sort("date")
    bbb = panel.filter(pl.col("sec_id") == "BBB").sort("date")

    # 1. Cross-security isolation: BBB's ATH must never see AAA's 999 spike.
    check(bbb.get_column("ath").max() < 50.0,
          f"leakage: BBB ath max {bbb.get_column('ath').max()} should be < 50 (AAA's 999 leaked in)")
    # AAA's ATH DOES reflect its own spike from bar 100 onward.
    check(aaa.get_column("ath").to_list()[150] >= 999.0, "AAA ath should reflect its own 999 spike")

    # 2. ATH monotonic non-decreasing within a security.
    a = aaa.get_column("ath").to_list()
    check(all(a[i] <= a[i + 1] for i in range(len(a) - 1)), "AAA ath not monotonic non-decreasing")

    # 3. Consistency: panel columns == gated functions applied to AAA (catches alignment bugs).
    closes = [float(x) for x in aaa.get_column("close").to_list()]
    rows_dc = [{"date": d.isoformat(), "close": c, "high": h, "low": lo}
               for d, c, h, lo in zip(aaa.get_column("date").to_list(), closes,
                                      aaa.get_column("high").to_list(), aaa.get_column("low").to_list())]
    for col, length in (("ema60", 60), ("ema200", 200)):
        exp = fx.ema(closes, {"length": length})
        got = aaa.get_column(col).to_list()
        check(got == exp, f"{col} column != fx.ema(length={length}) for AAA")
    exp_p = fx.perf_calendar(rows_dc, {"months": 3})
    check(aaa.get_column("perf_3m").to_list() == exp_p, "perf_3m column != fx.perf_calendar(3) for AAA")

    # 4. Warmup nulling + ratio null-propagation: ema200 null for the first 199 bars, and ext60 null
    #    exactly where ema60 is null; non-null & correct where ema60 is present.
    e200 = aaa.get_column("ema200").to_list()
    check(all(v is None for v in e200[:199]) and e200[199] is not None,
          "ema200 warmup nulling wrong (expect null for first 199 bars, value at bar 200)")
    e60 = aaa.get_column("ema60").to_list()
    ext = aaa.get_column("ext60").to_list()
    cl = closes
    for i in range(len(cl)):
        if e60[i] is None:
            check(ext[i] is None, f"ext60[{i}] should be null while ema60 is null")
        else:
            expv = (cl[i] / e60[i] - 1) * 100
            check(ext[i] is not None and abs(ext[i] - expv) < 1e-9, f"ext60[{i}] mismatch")

    # 5. Sanity: low_52w <= close <= high_52w everywhere.
    bad = panel.filter(~((pl.col("low_52w") <= pl.col("close")) & (pl.col("close") <= pl.col("high_52w"))))
    check(bad.height == 0, f"{bad.height} rows violate low_52w <= close <= high_52w")

    if FAILS:
        print(f"FAIL ({len(FAILS)} issue(s)):")
        for f in FAILS:
            print("  -", f)
        return 1
    print(f"PASS: panel self-test OK ({panel.height} rows, {len(panel.columns)} cols, 2 securities).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
