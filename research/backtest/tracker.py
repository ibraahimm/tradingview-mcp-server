"""Faithful Python reimplementation of the saudi-tracker.js journey + lifecycle state machine.

This is a CONFORMANT port, not a re-derivation: it mirrors `buildItems` in
.claude/scripts/saudi-tracker.js line-for-line and is proven against that JS via shared golden
vectors (research/spec/lifecycle_vectors/) + a JS<->Python differential test (selftest_tracker.py).

Scope = the COMMITTED methodology only: W1/W2 journeys (ACTIVE-W1/ACTIVE-W2/GRAD*/FAILED/STALE/
EXPIRED + NEW/PROMOTED/nearATH badges). W3-as-a-journey-stage was proposed in the Operational
Handoff but never committed to the tracker, so it is intentionally OUT of scope here (see
research/spec/lifecycle.md "Scope & adaptations").

The ONE adaptation versus the live tool: `as_of` (a date) replaces wall-clock `Date.now()`, so the
journey can be replayed point-in-time. With as_of = today the two are identical. All cadence / data
adaptations live in the (future) event-GENERATION layer, never in this state machine.
"""
from __future__ import annotations
import math
from datetime import datetime, timezone

DAY_MS = 86_400_000
GRAD_P5Y = 2000
STALE_DAYS = 120
HORIZON_DAYS = 1826  # ~5y


def ts(date_str: str) -> int:
    """Epoch ms at UTC midnight — matches JS Date.parse(date + 'T00:00:00Z')."""
    y, m, d = map(int, date_str.split("-"))
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)


def js_round(x, p):
    """Match JS Math.round(x*10**p)/10**p (half rounds toward +Infinity)."""
    if x is None:
        return None
    return math.floor(x * 10 ** p + 0.5) / 10 ** p


def _journey_string(evs) -> str:
    out = []
    for e in evs:
        if not out or out[-1] != e["source"]:
            out.append(e["source"])
    return "→".join(out)


def build_items(ledger, now_ms: int, grad_p5y=GRAD_P5Y, stale_days=STALE_DAYS, horizon_days=HORIZON_DAYS):
    """Roll the ledger into one journey + state per symbol. Faithful to saudi-tracker.js buildItems."""
    by_sym: dict = {}
    latest_date = ""
    for e in ledger:
        by_sym.setdefault(e["symbol"], []).append(e)
        if e["date"] > latest_date:
            latest_date = e["date"]

    items = []
    for sym, raw in by_sym.items():
        evs = sorted(raw, key=lambda a: a["ts"])
        first, last = evs[0], evs[-1]
        first_close = first.get("first_close")
        if first_close is None:
            first_close = first["close"]
        first_seen = first.get("first_seen") or first["date"]
        gain = ((last["close"] / first_close - 1) * 100) if first_close else None
        has_w1 = any(e["source"] == "W1" for e in evs)
        has_w2 = any(e["source"] == "W2" for e in evs)
        vs200 = None
        for e in reversed(evs):
            if e.get("vs200") is not None:
                vs200 = e["vs200"]
                break
        p5y = last.get("Perf.5Y")
        age_days = (now_ms - ts(first_seen)) / DAY_MS
        since_last = (now_ms - ts(last["date"])) / DAY_MS

        grad_flag = p5y is not None and p5y > grad_p5y
        failed = vs200 is not None and last["close"] < first_close and vs200 < 0
        expired = age_days > horizon_days and not grad_flag
        stale = (not failed) and (not grad_flag) and since_last > stale_days
        if failed:
            state = "FAILED"
        elif grad_flag:
            state = "GRAD★"
        elif expired:
            state = "EXPIRED"
        elif stale:
            state = "STALE"
        else:
            state = "ACTIVE-W2" if last["source"] == "W2" else "ACTIVE-W1"

        items.append({
            "symbol": sym, "name": last.get("name"), "first_seen": first_seen,
            "journey": _journey_string(evs), "runs": len(evs), "first_close": first_close,
            "close": last["close"], "gain": gain, "belowATH": last.get("belowATH"),
            "offLow": last.get("offLow"), "p5y": p5y, "vs200": vs200, "state": state,
            "isNew": first_seen == latest_date, "promoted": has_w1 and has_w2,
            "nearATH": last.get("belowATH") is not None and last.get("belowATH") < 10,
        })
    items.sort(key=lambda r: r["gain"] if r["gain"] is not None else -1e9, reverse=True)
    return items, latest_date


def conform(ledger, as_of: str, grad_p5y=GRAD_P5Y, stale_days=STALE_DAYS, horizon_days=HORIZON_DAYS):
    """Per-symbol journey/state dict (keyed + ordered by symbol) matching saudi-tracker.js stage=conform."""
    items, _ = build_items(ledger, ts(as_of), grad_p5y, stale_days, horizon_days)
    out = {}
    for r in sorted(items, key=lambda r: r["symbol"]):
        out[r["symbol"]] = {
            "state": r["state"], "journey": r["journey"], "runs": r["runs"],
            "gain": js_round(r["gain"], 4), "first_close": r["first_close"], "close": r["close"],
            "belowATH": r["belowATH"], "offLow": r["offLow"], "p5y": r["p5y"], "vs200": r["vs200"],
            "isNew": r["isNew"], "promoted": r["promoted"], "nearATH": r["nearATH"],
        }
    return out
