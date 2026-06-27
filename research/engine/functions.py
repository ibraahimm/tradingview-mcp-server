"""Polars implementations of the canonical spec's algorithms (../spec/features.yaml).

Scope (minimal, W1/stage2): the three algorithm families the golden vectors gate —
`ema`, `perf_calendar`, and the structural `ratios`. Window anchors (ath / 52-week
extremes) and the full panel assembly are a separate, later increment and MUST arrive
with their own golden vectors before they are added here (see README).

Boundary I/O matches the FUNCTIONS adapter contract (lists / row-dicts in and out);
Polars is used internally so the same definitions vectorize over a full panel later.
The spec wins all semantics; any divergence from TradingView is a monitored delta
(../validation/CONFORMANCE.md), never resolved by editing a definition here.
"""
from __future__ import annotations
import calendar
from datetime import date
from typing import Optional

import polars as pl


# --------------------------------------------------------------------------- ema
def ema(closes, params) -> list:
    """spec function `ema`: alpha=2/(length+1); ema[0]=close[0]; recursive; null while
    bar_count < length. Polars ewm_mean(adjust=False) gives the first-value seed + recursion;
    we null the warmup window explicitly to match the spec exactly."""
    length = int(params["length"])
    s = pl.Series("close", [float(c) for c in closes])
    out = s.ewm_mean(alpha=2.0 / (length + 1.0), adjust=False).to_list()
    for i in range(min(length - 1, len(out))):     # emit null until bar_count >= length
        out[i] = None
    return out


# ------------------------------------------------------------------ perf_calendar
def _sub_months(d: date, months: int) -> date:
    total = (d.year * 12 + (d.month - 1)) - months
    y, m = total // 12, total % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def perf_calendar(rows, params) -> list:
    """spec function `perf_calendar`: target = date - `months`; ref = close on the last
    trading day <= target (as-of-or-before); perf = (close/ref - 1)*100; null when target
    precedes the first bar. Implemented as a Polars backward as-of join."""
    months = int(params["months"])
    n = len(rows)
    dates = [date.fromisoformat(r["date"]) for r in rows]
    closes = [float(r["close"]) for r in rows]
    targets = [_sub_months(d, months) for d in dates]

    left = pl.DataFrame({"i": list(range(n)), "target": targets, "close": closes}).sort("target")
    right = pl.DataFrame({"ref_date": dates, "ref_close": closes}).sort("ref_date")
    joined = (
        left.join_asof(right, left_on="target", right_on="ref_date", strategy="backward")
        .with_columns(perf=(pl.col("close") / pl.col("ref_close") - 1) * 100)
        .sort("i")
    )
    return joined.get_column("perf").to_list()     # None where no ref (target < first date)


# ----------------------------------------------------------------------- ratios
# Single source of truth for the structural ratios: Polars expressions over panel columns.
# The conformance adapter evaluates them on a 1-row frame; the panel builder will reuse the
# SAME dict vectorized over all rows. Null propagation is automatic (any null input -> null).
RATIO_EXPRS = {
    "ddmax":    (pl.col("ath") - pl.col("low_52w")) / pl.col("ath") * 100,
    "below_ath": (pl.col("ath") - pl.col("close")) / pl.col("ath") * 100,
    "off_low":  (pl.col("close") / pl.col("low_52w") - 1) * 100,
    "nrhi":     pl.col("close") / pl.col("high_52w") * 100,
    "ext60":    (pl.col("close") / pl.col("ema60") - 1) * 100,
    "ema21gap": (pl.col("close") / pl.col("ema21") - 1) * 100,
    "ema_comp": (pl.col("ema21") / pl.col("ema60") - 1) * 100,
    "vs200":    (pl.col("close") / pl.col("ema200") - 1) * 100,
}
_RATIO_INPUTS = ("close", "ath", "low_52w", "high_52w", "ema21", "ema60", "ema200")


def ratios(row) -> dict:
    """spec `ratios`: evaluate RATIO_EXPRS for one bar (row-dict of input columns)."""
    cols = {k: (None if row.get(k, "") in ("", None) else float(row[k])) for k in _RATIO_INPUTS}
    out = pl.DataFrame([cols]).select([e.alias(name) for name, e in RATIO_EXPRS.items()])
    rec = out.row(0, named=True)
    return {k: (None if v is None else float(v)) for k, v in rec.items()}
