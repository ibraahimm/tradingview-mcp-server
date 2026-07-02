"""Screen run: turn the feature panel + rules into a reproducible TASI-W1/TASI-W2/TASI-W3 run.

Enriches the price-feature panel with the two non-price inputs the rules need, then evaluates a
rule over it (funnel + survivors):

  age_years = (date - list_date) / 365.25            # from the reference layer (security_master)
  value     = mean(volume over `window` bars) * close # trailing ADV in SAR, per security

Both definitions are pinned by `selftest_screen.py`. age_years/value live here (not in
features.yaml) because they are reference/liquidity derivations, not price-derived per-bar
features. The rule logic itself is the gated engine (rules.py); this module is the join + run.
"""
from __future__ import annotations

import polars as pl

from . import rules as R

YEAR_DAYS = 365.25


def compute_age_years(panel: pl.DataFrame, security_master: pl.DataFrame) -> pl.DataFrame:
    """Join `list_date` (security_master: sec_id, list_date as pl.Date) and add `age_years` as-of
    each bar's date. Null where list_date is unknown (-> the age gate drops it)."""
    sm = security_master.select(["sec_id", "list_date"])
    return panel.join(sm, on="sec_id", how="left").with_columns(
        age_years=(pl.col("date") - pl.col("list_date")).dt.total_days() / YEAR_DAYS
    )


def compute_value(panel: pl.DataFrame, window: int = 30) -> pl.DataFrame:
    """Add `value` = trailing mean(volume) over `window` bars (per sec_id) * close, in SAR.
    Null until `window` bars exist (trailing-only; no look-ahead)."""
    p = panel.sort(["sec_id", "date"])
    idx = pl.int_range(pl.len()).over("sec_id")
    adv = pl.col("volume").rolling_mean(window_size=window).over("sec_id")
    return p.with_columns(
        value=pl.when(idx >= window - 1).then(adv * pl.col("close")).otherwise(None)
    )


def run_screen(panel: pl.DataFrame, security_master: pl.DataFrame, rule_name: str,
               params_overrides: dict | None = None, value_window: int = 30):
    """Enrich + evaluate. Returns (survivors, funnel_steps, decided):
      survivors  - rows where passed == True
      funnel     - [(step_label, n_alive), ...] from 'base' through each enabled gate
      decided    - the full enriched frame with `passed` + `first_fail` columns
    """
    rule = R.load_rules()[rule_name]
    enriched = compute_value(compute_age_years(panel, security_master), window=value_window)
    funnel = R.funnel(rule, enriched, params_overrides)
    decided = R.evaluate_frame(rule, enriched, params_overrides)
    survivors = decided.filter(pl.col("passed"))
    return survivors, funnel, decided
