"""Rule engine: evaluate the canonical W1/W2/W3 screen rules (../spec/rules.yaml).

Pure, ordered predicate evaluation over a feature row (a dict feature->value, None = null).
Features come from the panel (price-derived) plus the reference/liquidity layer (age_years,
value). The rule fixtures (../spec/rule_vectors) are the acceptance gate. Spec wins; conformance
to TradingView's own pass/fail is a separate concern (the forward oracle).
"""
from __future__ import annotations
from pathlib import Path

import yaml

_RULES_PATH = Path(__file__).resolve().parents[1] / "spec" / "rules.yaml"

_OPS = {
    "ge": lambda x, a: x >= a,
    "gt": lambda x, a: x > a,
    "le": lambda x, a: x <= a,
    "lt": lambda x, a: x < a,
    "in_co": lambda x, a: a[0] <= x < a[1],   # [lo, hi)
    "in_oo": lambda x, a: a[0] < x < a[1],     # (lo, hi)
    "in_cc": lambda x, a: a[0] <= x <= a[1],   # [lo, hi]
}
_GUARD_OPS = {">": "gt", "<": "lt", ">=": "ge", "<=": "le"}


def load_rules(path: Path | None = None) -> dict:
    """Load the W1/W2/W3 rule definitions from the canonical rules.yaml."""
    return yaml.safe_load((path or _RULES_PATH).read_text())["rules"]


def _resolve(value, params):
    if isinstance(value, list):
        return [_resolve(v, params) for v in value]
    if isinstance(value, str) and value.startswith("@"):
        return params[value[1:]]
    return value


def _enabled(pred: dict, params: dict) -> bool:
    ew = pred.get("enabled_when")
    if not ew:
        return True
    name, op, num = ew.split()
    return _OPS[_GUARD_OPS[op]](params[name], float(num))


def evaluate(rule: dict, row: dict, params_overrides: dict | None = None):
    """Evaluate one rule against one feature row.

    Returns (passed: bool, first_fail: str | None). The funnel is evaluated in order; the first
    enabled predicate that fails stops evaluation and names its gate. Null inputs are handled per
    each predicate's `null_action` (skip = pass-through, drop = fail). Disabled predicates
    (enabled_when false) are skipped entirely.
    """
    params = dict(rule["params"])
    if params_overrides:
        params.update(params_overrides)
    for pred in rule["funnel"]:
        if not _enabled(pred, params):
            continue
        feat = pred["feature"]
        if feat not in row:
            raise KeyError(f"row is missing required feature '{feat}'")
        x = row[feat]
        if x is None:
            if pred.get("null_action") == "skip":
                continue
            return (False, feat)
        if not _OPS[pred["op"]](x, _resolve(pred["value"], params)):
            return (False, feat)
    return (True, None)


def evaluate_frame(rule: dict, df, params_overrides: dict | None = None):
    """Apply `evaluate` row-wise over a Polars frame (which must carry the rule's feature columns).
    Returns the frame with `passed` (Boolean) and `first_fail` (Utf8, null when passed) appended."""
    import polars as pl

    res = [evaluate(rule, r, params_overrides) for r in df.iter_rows(named=True)]
    return df.with_columns(
        passed=pl.Series([p for p, _ in res], dtype=pl.Boolean),
        first_fail=pl.Series([f for _, f in res], dtype=pl.Utf8),
    )


def funnel(rule: dict, df, params_overrides: dict | None = None):
    """Ordered survivor counts: [(step_label, n_alive), ...] starting from 'base', one entry per
    enabled gate — the same funnel the live screens print."""
    params = dict(rule["params"])
    if params_overrides:
        params.update(params_overrides)
    rows = list(df.iter_rows(named=True))
    alive = [True] * len(rows)
    steps = [("base", sum(alive))]
    for pred in rule["funnel"]:
        if not _enabled(pred, params):
            continue
        feat = pred["feature"]
        for i, r in enumerate(rows):
            if not alive[i]:
                continue
            x = r.get(feat)
            if x is None:
                if pred.get("null_action") != "skip":
                    alive[i] = False
                continue
            if not _OPS[pred["op"]](x, _resolve(pred["value"], params)):
                alive[i] = False
        steps.append((feat, sum(alive)))
    return steps
