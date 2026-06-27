"""Event-study core: forward-return labeling + aggregation. See README.md for the definition.

Pure Polars over a panel + the reference security_master (for delisting terminal values).
No look-ahead beyond the explicit horizon; right-censored signals are nulled, not fabricated.
"""
from __future__ import annotations
import statistics

import polars as pl


def label_forward_returns(panel: pl.DataFrame, security_master: pl.DataFrame,
                          horizons=(20, 60, 120)) -> pl.DataFrame:
    """Add a `fwd_<H>` price-return column for each horizon H (trading days), per security:
      - close[t+H]/close[t]-1            when a bar exists H ahead
      - terminal_value/close[t]-1        when past the last bar of a DELISTED security
      - null                             when right-censored (still listed, data ended)
    """
    sm = security_master.select(["sec_id", "delist_date", "terminal_value"])
    p = panel.sort(["sec_id", "date"]).join(sm, on="sec_id", how="left")
    is_delisted = pl.col("delist_date").is_not_null() & pl.col("terminal_value").is_not_null()
    out = []
    for h in horizons:
        fwd_close = pl.col("close").shift(-h).over("sec_id")
        out.append(
            pl.when(fwd_close.is_not_null())
            .then((fwd_close / pl.col("close") - 1) * 100)
            .when(is_delisted)
            .then((pl.col("terminal_value") / pl.col("close") - 1) * 100)
            .otherwise(None)
            .alias(f"fwd_{h}")
        )
    return p.with_columns(out)


def aggregate(labeled: pl.DataFrame, horizon: int, mask: pl.Expr | None = None) -> dict:
    """{n, hit_rate, mean, median} over non-null fwd_<horizon> (optionally filtered by `mask`)."""
    df = labeled.filter(mask) if mask is not None else labeled
    vals = [v for v in df.get_column(f"fwd_{horizon}").to_list() if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0, "hit_rate": None, "mean": None, "median": None}
    return {
        "n": n,
        "hit_rate": sum(1 for v in vals if v > 0) / n * 100,
        "mean": sum(vals) / n,
        "median": statistics.median(vals),
    }


def event_study(labeled: pl.DataFrame, horizon: int, signal_col: str = "passed") -> dict:
    """A/B at `horizon`: aggregate over signals (rule survivors) vs the rest. The out-of-sample
    answer to 'do this gate's survivors out-perform?' — `signals.mean - rest.mean` is the edge."""
    return {
        "signals": aggregate(labeled, horizon, pl.col(signal_col)),
        "rest": aggregate(labeled, horizon, ~pl.col(signal_col)),
    }
