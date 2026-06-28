"""Market-regime layer — conditions the W1/W2 evaluation on the *systemic* environment.

WHY: the rigor/robust passes conditioned only on each NAME's own deep correction (per-name DDmax/
belowATH/offLow) and pooled signals across all of 2001-2026. That answers "do idiosyncratically
corrected names earn an edge on average?" It does NOT answer the original W1 thesis — "deep-correction
names bought when the *whole market* is in crisis / deep drawdown outperform as it recovers." This
layer builds a point-in-time market regime and lets the driver partition signals by it.

PRE-REGISTERED CHOICES (fixed BEFORE looking at any conditional result — no threshold fishing):

  * Market proxy = equal-weight index of daily cross-sectional mean returns (clipped at +/-30% per
    name/day to stop a single penny-stock print dominating). This is the SAME equal-weight cohort the
    benchmark already neutralizes against in add_excess, so regime and benchmark are consistent.

  * Drawdown is measured from a TRAILING 252-day high, NOT the all-time high. Reason (structural, not
    result-driven): the 2006 TASI bubble left the market below its all-time peak for ~a decade, so an
    ATH-anchored drawdown would label almost all of 2006-2021 as "deep drawdown" and the regime would
    be a near-constant. A rolling 1y high captures ACUTE drawdowns (the crises) and resets on recovery,
    which is exactly the "crisis then recovery" notion the W1 thesis is about.

  * Regime cuts (the small fixed set, as agreed): dd >= 20%, dd >= 35%, and below-EMA200 (level <
    its 200-span EMA). "normal" = dd < 20%. These are declared here, not swept.

  * Crisis EPISODES for leave-one-crisis-out are fixed calendar windows around the four acute Saudi
    drawdowns (2006, 2008, 2014-15, 2020). A crisis-regime signal outside every window is "other".

All series are point-in-time: dd[t] / ema[t] use only bars up to t (rolling/ewm are causal), and
mkt_fwd_<h>[t] = level[t+h]/level[t]-1 is the realized forward path (right-censored at the tail).

Gated by selftest_regime.py. Consumed by research/regime_run.py.
"""
from __future__ import annotations
from datetime import date

import polars as pl

# Fixed crisis windows (acute Saudi drawdowns) for leave-one-crisis-out. Generous, declared up front.
EPISODES: list[tuple[str, date, date]] = [
    ("2006", date(2006, 2, 1), date(2007, 12, 31)),
    ("2008", date(2008, 5, 1), date(2009, 12, 31)),
    ("2014-15", date(2014, 9, 1), date(2016, 1, 31)),
    ("2020", date(2020, 2, 1), date(2020, 12, 31)),
]
EPISODE_NAMES = [e[0] for e in EPISODES]


def episode_of(d: date) -> str:
    for name, a, b in EPISODES:
        if a <= d <= b:
            return name
    return "other"


def build_market(prices: pl.DataFrame, ret_clip: float = 0.30,
                 roll_win: int = 252, ema_span: int = 200) -> pl.DataFrame:
    """Equal-weight market proxy + point-in-time drawdown/trend regime descriptors.

    Returns per-date: mkt_ret, n_names, mkt_level, roll_high, dd (depth >=0 from trailing high),
    ema200, below_ema200."""
    p = (prices.select(["date", "sec_id", "close"]).sort(["sec_id", "date"])
         .with_columns(ret=(pl.col("close") / pl.col("close").shift(1).over("sec_id") - 1))
         .with_columns(ret=pl.col("ret").clip(-ret_clip, ret_clip)))
    mk = (p.group_by("date").agg(mkt_ret=pl.col("ret").mean(), n_names=pl.col("ret").count())
          .sort("date")
          .with_columns(mkt_ret=pl.col("mkt_ret").fill_null(0.0)))
    mk = mk.with_columns(mkt_level=(1.0 + pl.col("mkt_ret")).cum_prod())
    mk = mk.with_columns(
        roll_high=pl.col("mkt_level").rolling_max(window_size=roll_win, min_periods=1),
        ema200=pl.col("mkt_level").ewm_mean(span=ema_span, adjust=False),
    )
    mk = mk.with_columns(
        dd=(1.0 - pl.col("mkt_level") / pl.col("roll_high")),
        below_ema200=(pl.col("mkt_level") < pl.col("ema200")),
    )
    return mk


def market_forward(mk: pl.DataFrame, horizons) -> pl.DataFrame:
    """Add mkt_fwd_<h> = (level[t+h]/level[t]-1)*100 — the market's own realized forward return (the
    beta-1 benchmark for the directional reading). Right-censored at the tail (null)."""
    out = mk
    for h in horizons:
        out = out.with_columns(
            ((pl.col("mkt_level").shift(-h) / pl.col("mkt_level") - 1) * 100).alias(f"mkt_fwd_{h}")
        )
    return out


def assign_regimes(mk: pl.DataFrame, dd20: float = 0.20, dd35: float = 0.35) -> pl.DataFrame:
    """Boolean regime columns from the fixed cuts: reg_dd20, reg_dd35, reg_below200, reg_normal."""
    return mk.with_columns(
        reg_dd20=(pl.col("dd") >= dd20),
        reg_dd35=(pl.col("dd") >= dd35),
        reg_below200=pl.col("below_ema200"),
        reg_normal=(pl.col("dd") < dd20),
    )


REGIME_COLS = ["reg_dd20", "reg_dd35", "reg_below200", "reg_normal"]


def market_table(prices: pl.DataFrame, horizons) -> pl.DataFrame:
    """One call: proxy -> forward returns -> regime flags. The per-date table the driver joins on date."""
    return assign_regimes(market_forward(build_market(prices), horizons))
