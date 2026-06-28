"""Sequential-lifecycle layer — evaluates W1/W2/W3 as ONE pipeline of successive filters, not three
independent screens.

The design intent (recorded): collapse -> W1 (initial recovery ENTRY/timing) -> W2 (confirmation the
recovery is becoming healthy) -> W3 (the name has exited the crisis into NORMAL trend). So we must
measure the INCREMENTAL value of each stage along the lifecycle, not each wave standalone.

Two complementary views, both produced here:

  TRADEABLE (look-ahead-free) — each stage is entered at the moment ITS OWN gate fires, conditional on
  the earlier stage(s) having fired in the PAST (within the link window K). Populations:
      W1        : every W1 trigger.
      W1->W2    : a W2 trigger that had a W1 trigger in [t-K, t] for the same name (enter at the W2 bar).
      W1->W2->W3: a W3 trigger that had a *linked* W2 in [t-K, t] (which itself followed a W1).
  Answers "is entering at the more-confirmed, later stage better timing?" — never uses the future.

  DIAGNOSTIC (uses the future BY CONSTRUCTION — labelled, not tradeable) — take the W1 entries and split
  them by whether the name LATER (within K) progressed to W2 / W3. Answers "does the W2/W3 transition
  identify the W1 entries that worked, i.e. filter failed recoveries from successful ones?"

`link_stages` is the pure, unit-tested core (operates on per-name trading-day-index lists). Gated by
selftest_lifecycle.py; consumed by research/lifecycle_run.py.
"""
from __future__ import annotations
from collections import defaultdict

import polars as pl


def link_stages(p1: dict, p2: dict, p3: dict, K: int) -> dict:
    """Pure lifecycle linkage over per-name trading-day-index lists.

    p1/p2/p3: {sec_id -> sorted list of td_idx where W1/W2/W3 passes}. K: max trading-day gap linking a
    stage to the prior stage. Returns sets of (sec_id, td_idx):
      w1        : all W1 triggers
      w2        : W2 triggers with a W1 in [b-K, b]            (linked, enter-at-W2)
      w3        : W3 triggers with a linked W2 in [c-K, c]     (chain W1->W2->W3, enter-at-W3)
      w1_conf2  : W1 entries that LATER (within K) reach W2     (diagnostic; uses future)
      w1_conf3  : W1 entries whose lifecycle LATER reaches W3   (diagnostic; uses future)
    Linkage requires the prior stage at-or-before the later one (a <= b), i.e. strictly causal for the
    tradeable sets."""
    w1, w2, w3, w1_conf2, w1_conf3 = set(), set(), set(), set(), set()
    names = set(p1) | set(p2) | set(p3)
    for name in names:
        i1 = p1.get(name, [])
        i2 = p2.get(name, [])
        i3 = p3.get(name, [])
        for a in i1:
            w1.add((name, a))
        # tradeable linked W2: a W2 bar b with some W1 a in [b-K, b]
        linked2 = []
        for b in i2:
            if any(a <= b <= a + K for a in i1):
                linked2.append(b)
                w2.add((name, b))
        # tradeable linked W3: a W3 bar c with some linked W2 b in [c-K, c]
        for c in i3:
            if any(b <= c <= b + K for b in linked2):
                w3.add((name, c))
        # diagnostic: a W1 entry a "confirms W2" if some W2 b in (a, a+K]; "confirms W3" if the chain reaches W3
        for a in i1:
            c2 = [b for b in i2 if a <= b <= a + K]
            if c2:
                w1_conf2.add((name, a))
                if any(any(b <= c <= b + K for c in i3) for b in c2):
                    w1_conf3.add((name, a))
    return {"w1": w1, "w2": w2, "w3": w3, "w1_conf2": w1_conf2, "w1_conf3": w1_conf3}


def _passes(decided: pl.DataFrame) -> dict:
    """{sec_id -> sorted [td_idx]} for the rows where `passed` is true."""
    m = defaultdict(list)
    for sid, idx in (decided.filter(pl.col("passed")).select(["sec_id", "td_idx"]).iter_rows()):
        m[sid].append(idx)
    for k in m:
        m[k].sort()
    return m


def _mark(labeled: pl.DataFrame, pairs: set, col: str) -> pl.DataFrame:
    """Add a boolean column `col` true exactly on the (sec_id, td_idx) members of `pairs`."""
    if not pairs:
        return labeled.with_columns(pl.lit(False).alias(col))
    key = pl.DataFrame({"sec_id": [p[0] for p in pairs], "td_idx": [p[1] for p in pairs]},
                       schema={"sec_id": pl.Utf8, "td_idx": pl.Int64}).with_columns(pl.lit(True).alias(col))
    return labeled.join(key, on=["sec_id", "td_idx"], how="left").with_columns(pl.col(col).fill_null(False))


def mark_stages(labeled: pl.DataFrame, dW1, dW2, dW3, K: int) -> pl.DataFrame:
    """Tag `labeled` with the tradeable stage columns (stg_w1/stg_w2/stg_w3) and the diagnostic W1-entry
    confirmation columns (w1_conf2/w1_conf3). `td_idx` must already be present."""
    links = link_stages(_passes(dW1), _passes(dW2), _passes(dW3), K)
    out = labeled
    for pairs, col in ((links["w1"], "stg_w1"), (links["w2"], "stg_w2"), (links["w3"], "stg_w3"),
                       (links["w1_conf2"], "w1_conf2"), (links["w1_conf3"], "w1_conf3")):
        out = _mark(out, pairs, col)
    return out
