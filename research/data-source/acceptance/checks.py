#!/usr/bin/env python3
"""Vendor acceptance checks — turn the MUST requirements (../REQUIREMENTS.md) into automated
pass/fail over a vendor TRIAL sample. Stdlib only.

Sample contract (CSV files in a sample directory; see README.md):
  securities.csv        vendor_id, ticker, name, list_date, delist_date, delist_reason, terminal_value
  prices.csv            vendor_id, date, open, high, low, close, close_unadj, adj_factor, volume
  corporate_actions.csv vendor_id, ca_type, ex_date, ratio, amount
  ticker_history.csv    vendor_id, ticker, valid_from, valid_to

Adjustment contract (what we ask the vendor to deliver / normalize to):
  close = close_unadj * adj_factor      (adjusted = unadjusted x factor; factor accumulates splits)

MUST checks (gating): R1 survivorship/2006, R2 adj+unadj, R3 corporate-action reconciliation,
R4 identifier continuity, R6 delisting metadata. PARTIAL checks (informational, need human
follow-up): R5 calendar, R7 reconcilable.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

TODAY = date.today().isoformat()
COVERAGE_FLOOR = "2006-12-31"   # R1: history must span the 2006 cycle


def _load(sample_dir, name):
    p = Path(sample_dir) / f"{name}.csv"
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f))


def _f(v):
    return None if v in (None, "") else float(v)


# ---------------------------------------------------------------- MUST checks
def check_R1(securities, prices):
    """Survivorship-free: delisted names present, history spans 2006, names not listed today."""
    if not securities or not prices:
        return False, "missing securities or prices table"
    delisted = [s for s in securities if s.get("delist_date")]
    dates = [p["date"] for p in prices if p.get("date")]
    earliest = min(dates) if dates else None
    spans_2006 = earliest is not None and earliest <= COVERAGE_FLOOR
    not_listed_today = any(s["delist_date"] < TODAY for s in delisted)
    ok = bool(delisted) and spans_2006 and not_listed_today
    return ok, (f"delisted={len(delisted)}, earliest={earliest} (<=2006: {spans_2006}), "
                f"not-listed-today={not_listed_today}")


def check_R2(prices, corporate_actions):
    """Adjusted AND unadjusted: required columns present; across a split, unadjusted jumps by the
    ratio while adjusted close stays continuous."""
    if not prices:
        return False, "no prices table"
    cols = set(prices[0].keys())
    need = {"close", "close_unadj", "adj_factor"}
    if not need <= cols:
        return False, f"missing columns {sorted(need - cols)} (need both adjusted and unadjusted)"
    splits = [c for c in corporate_actions if c.get("ca_type") == "split"]
    if not splits:
        return False, "no split in sample to verify adjustment continuity (request a name with a split)"
    sp = splits[0]
    ratio = _f(sp.get("ratio"))
    series = sorted([p for p in prices if p["vendor_id"] == sp["vendor_id"]], key=lambda r: r["date"])
    idx = next((i for i, p in enumerate(series) if p["date"] >= sp["ex_date"]), None)
    if not idx:  # None or 0 -> ex_date not bracketed by a prior bar
        return False, f"split ex_date {sp['ex_date']} not bracketed by prices for {sp['vendor_id']}"
    prev, at = series[idx - 1], series[idx]
    unadj_jump = _f(prev["close_unadj"]) / _f(at["close_unadj"])
    adj_cont = _f(at["close"]) / _f(prev["close"])
    ok = abs(unadj_jump - ratio) < 1e-2 and abs(adj_cont - 1.0) < 5e-2
    return ok, f"unadj jump={unadj_jump:.3f} (~ratio {ratio}); adjusted continuity={adj_cont:.3f} (~1.0)"


def check_R3(prices, corporate_actions):
    """Corporate actions reconcile the adjustment: reconstruct adj_factor from splits and confirm
    close == close_unadj * adj_factor for the split's security."""
    if not corporate_actions:
        return False, "no corporate_actions table"
    if not any(c.get("ex_date") and (c.get("ratio") or c.get("amount")) for c in corporate_actions):
        return False, "corporate actions lack ex_date + ratio/amount"
    splits = [c for c in corporate_actions if c.get("ca_type") == "split"]
    if not splits:
        return True, "corporate actions present (no split to reconcile; structure ok)"
    vid = splits[0]["vendor_id"]
    sp_for = [(c["ex_date"], _f(c["ratio"])) for c in splits if c["vendor_id"] == vid]
    mism = 0
    for p in [r for r in prices if r["vendor_id"] == vid]:
        factor = 1.0
        for ex, r in sp_for:
            if p["date"] < ex:
                factor /= r
        if abs(factor - _f(p["adj_factor"])) > 1e-6:
            mism += 1
        if abs(_f(p["close"]) - _f(p["close_unadj"]) * _f(p["adj_factor"])) > 1e-4:
            mism += 1
    return mism == 0, (f"reconstructed adj_factor matches vendor for {vid}"
                       if mism == 0 else f"{mism} reconciliation mismatch(es) for {vid}")


def check_R4(ticker_history):
    """Stable identifier independent of the reusable exchange code: vendor_id != ticker, a
    ticker change keeps the same vendor_id, and a code is never concurrently two vendor_ids."""
    if not ticker_history:
        return False, "no ticker_history table"
    by_vid = defaultdict(set)
    for t in ticker_history:
        by_vid[t["vendor_id"]].add(t["ticker"])
    change_demo = any(len(ts) > 1 for ts in by_vid.values())
    surrogate = all(t["vendor_id"] != t["ticker"] for t in ticker_history)
    by_tk = defaultdict(list)
    for t in ticker_history:
        by_tk[t["ticker"]].append((t["valid_from"], t.get("valid_to") or "9999-12-31", t["vendor_id"]))
    concurrent = False
    for iv in by_tk.values():
        iv.sort()
        for a, b in zip(iv, iv[1:]):
            if a[1] > b[0] and a[2] != b[2]:
                concurrent = True
    ok = surrogate and change_demo and not concurrent
    return ok, f"stable-surrogate={surrogate}, ticker-change-demo={change_demo}, concurrent-reuse={concurrent}"


def check_R6(securities):
    """Every delisted security carries a reason and a terminal value (for return labeling)."""
    delisted = [s for s in securities if s.get("delist_date")]
    if not delisted:
        return False, "no delisted securities present (also fails R1)"
    missing = [s["vendor_id"] for s in delisted if not (s.get("delist_reason") and s.get("terminal_value"))]
    return not missing, f"{len(delisted)} delisted; missing reason/terminal: {missing or 'none'}"


# ------------------------------------------------------------- PARTIAL checks
def check_R5(prices):
    """Partial: no duplicate (vendor_id, date). The holiday-calendar truth + the 2013 weekend
    change are a human/second-step check."""
    seen, dup = set(), False
    for p in prices:
        k = (p.get("vendor_id"), p.get("date"))
        if k in seen:
            dup = True
        seen.add(k)
    return (not dup), f"duplicate (id,date)={dup}; full holiday-calendar truth = human follow-up"


def check_R7(securities, prices):
    """Partial: structurally reconcilable (ticker + date keys present). The actual cross-vendor /
    TradingView reconciliation needs a second sample and is a human step."""
    ok = bool(securities) and bool(prices) and all("ticker" in s for s in securities)
    return ok, "structurally reconcilable (ticker+date); cross-vendor/TV check = human/second sample"


REQUIREMENTS = [
    ("R1", "MUST", "survivorship-free / delisted / 2006 span", check_R1, ("securities", "prices")),
    ("R2", "MUST", "adjusted AND unadjusted", check_R2, ("prices", "corporate_actions")),
    ("R3", "MUST", "corporate actions reconcile adjustment", check_R3, ("prices", "corporate_actions")),
    ("R4", "MUST", "identifier continuity", check_R4, ("ticker_history",)),
    ("R6", "MUST", "delisting metadata", check_R6, ("securities",)),
    ("R5", "PARTIAL", "trading calendar (partial)", check_R5, ("prices",)),
    ("R7", "PARTIAL", "reconcilable (partial)", check_R7, ("securities", "prices")),
]


def evaluate(sample_dir):
    """Run every check over a sample directory. Returns {req_id: {tier, label, passed, detail}}."""
    tables = {n: _load(sample_dir, n)
              for n in ("securities", "prices", "corporate_actions", "ticker_history")}
    out = {}
    for rid, tier, label, fn, args in REQUIREMENTS:
        passed, detail = fn(*[tables[a] for a in args])
        out[rid] = {"tier": tier, "label": label, "passed": passed, "detail": detail}
    return out
