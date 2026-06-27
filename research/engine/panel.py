"""Panel builder: assemble the (sec_id, date) feature panel from an adjusted OHLCV frame.

Reuses the golden-vector-gated functions (functions.py) PER SECURITY, so the panel is
correct by construction — every column is produced by the same code the vectors validate.
As-of discipline is enforced structurally: each security's series is computed in isolation
(group_by sec_id), so no value ever references another security or a future bar.

Minimal W1/stage2 feature set. Inputs are assumed adjusted (split/dividend) per the spec's
price_basis; survivorship/eligibility live in the reference layer, not here.
"""
from __future__ import annotations
from datetime import date

import polars as pl

from . import functions as fx

# Feature bindings — mirror ../spec/features.yaml (function + params).
EMA_LENGTHS = {"ema21": 21, "ema60": 60, "ema200": 200}
PERF_MONTHS = {
    "perf_1m": 1, "perf_3m": 3, "perf_6m": 6, "perf_1y": 12,
    "perf_3y": 36, "perf_5y": 60, "perf_10y": 120,
}
_REQUIRED = {"sec_id", "date", "high", "low", "close"}


def build_panel(prices: pl.DataFrame, ath_lookback_years: int | None = None) -> pl.DataFrame:
    """prices: one row per (sec_id, date) with columns sec_id, date (pl.Date), high, low, close
    (open/volume optional, carried through). Returns the panel with EMA / Perf / ATH / 52w /
    structural-ratio columns appended, sorted by (sec_id, date).

    `ath_lookback_years` optionally caps the ATH anchor to a trailing window (a strategy choice;
    default None = true all-time)."""
    missing = _REQUIRED - set(prices.columns)
    if missing:
        raise ValueError(f"prices missing required columns: {sorted(missing)}")

    groups = []
    for (_sec,), g in prices.sort(["sec_id", "date"]).group_by("sec_id", maintain_order=True):
        g = g.sort("date")
        dts = [d.isoformat() for d in g.get_column("date").to_list()]
        closes = [float(x) for x in g.get_column("close").to_list()]
        highs = [float(x) for x in g.get_column("high").to_list()]
        lows = [float(x) for x in g.get_column("low").to_list()]
        rows = [{"date": d, "close": c, "high": h, "low": lo}
                for d, c, h, lo in zip(dts, closes, highs, lows)]

        cols: dict[str, list] = {}
        for name, length in EMA_LENGTHS.items():
            cols[name] = fx.ema(closes, {"length": length})
        for name, months in PERF_MONTHS.items():
            cols[name] = fx.perf_calendar(rows, {"months": months})
        ath_params = {"field": "high"}
        if ath_lookback_years:
            ath_params["lookback_years"] = ath_lookback_years
        cols["ath"] = fx.running_max(rows, ath_params)
        cols["high_52w"] = fx.rolling_extreme(rows, {"field": "high", "weeks": 52, "op": "max"})
        cols["low_52w"] = fx.rolling_extreme(rows, {"field": "low", "weeks": 52, "op": "min"})

        groups.append(g.with_columns([pl.Series(k, v, dtype=pl.Float64) for k, v in cols.items()]))

    panel = pl.concat(groups)
    # Structural ratios — the SAME RATIO_EXPRS as the conformance adapter, now vectorized over the
    # whole frame. Null-propagating: a ratio is null wherever an input (e.g. ema60 in warmup) is null.
    panel = panel.with_columns([e.alias(n) for n, e in fx.RATIO_EXPRS.items()])
    return panel.sort(["sec_id", "date"])
