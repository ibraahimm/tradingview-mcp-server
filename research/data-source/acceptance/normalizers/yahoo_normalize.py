#!/usr/bin/env python3
"""Normalize Yahoo Finance Saudi (.SR) data into the acceptance-harness sample contract.

Empirical bridge used to TEST a free source against the MUST gates (see ../README.md). Fetches
daily bars + split/dividend events from Yahoo's public chart API and writes the four sample CSVs.
Requires network; NOT a CI gate. Yahoo data is fetched for evaluation only (not redistributed).

    python yahoo_normalize.py <out_dir> 2222.SR 1120.SR 2010.SR 4280.SR 1040.SR [start_year]

Mapping to the contract:
  vendor_id  = ticker          (Yahoo has no stable surrogate id -> exposes the R4 gap)
  close      = adjClose        (Yahoo's adjusted close: split+dividend adjusted)
  close_unadj= raw close
  adj_factor = adjClose/close  (so close == close_unadj * adj_factor holds by construction)
  list_date  = first bar date  (a proxy; Yahoo carries no true listing/delisting facts)
  delisted names -> Yahoo returns HTTP 404 (logged, and ABSENT from the sample -> exposes R1)
"""
from __future__ import annotations
import csv, json, sys, time, urllib.request
from datetime import date, timezone, datetime
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits"


def fetch(sym, start_year):
    p1 = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(time.time())
    url = CHART.format(sym=sym.replace("^", "%5E"), p1=p1, p2=p2)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def main():
    out = Path(sys.argv[1])
    args = sys.argv[2:]
    start_year = 2005
    if args and args[-1].isdigit():
        start_year = int(args.pop())
    syms = args
    out.mkdir(parents=True, exist_ok=True)

    securities, prices, cas, ticker_hist = [], [], [], []
    unavailable = []
    for sym in syms:
        d, err = fetch(sym, start_year)
        if err or not d or not d.get("chart", {}).get("result"):
            unavailable.append((sym, err or "no data"))
            continue
        r = d["chart"]["result"][0]
        ts = r.get("timestamp") or []
        q = r["indicators"]["quote"][0]
        adj = r["indicators"]["adjclose"][0]["adjclose"]
        ev = r.get("events", {})
        if not ts:
            unavailable.append((sym, "empty"))
            continue
        first = date.fromtimestamp(ts[0]).isoformat()
        tk = sym.replace(".SR", "")
        securities.append(dict(vendor_id=sym, ticker=tk, name=r["meta"].get("longName", sym),
                               list_date=first, delist_date="", delist_reason="", terminal_value=""))
        ticker_hist.append(dict(vendor_id=sym, ticker=tk, valid_from=first, valid_to=""))
        for i, t in enumerate(ts):
            c, a = q["close"][i], adj[i]
            if c is None or a is None:
                continue
            prices.append(dict(vendor_id=sym, date=date.fromtimestamp(t).isoformat(),
                               open=q["open"][i], high=q["high"][i], low=q["low"][i],
                               close=round(a, 6), close_unadj=round(c, 6),
                               adj_factor=round(a / c, 8), volume=q["volume"][i]))
        for t, s in (ev.get("splits") or {}).items():
            cas.append(dict(vendor_id=sym, ca_type="split", ex_date=date.fromtimestamp(int(t)).isoformat(),
                            ratio=s.get("numerator", 0) / s.get("denominator", 1), amount=""))
        for t, dv in (ev.get("dividends") or {}).items():
            cas.append(dict(vendor_id=sym, ca_type="dividend",
                            ex_date=date.fromtimestamp(int(t)).isoformat(), ratio="", amount=dv.get("amount")))

    def write(name, rows, cols):
        with (out / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

    write("securities", securities, ["vendor_id", "ticker", "name", "list_date", "delist_date", "delist_reason", "terminal_value"])
    write("prices", prices, ["vendor_id", "date", "open", "high", "low", "close", "close_unadj", "adj_factor", "volume"])
    write("corporate_actions", cas, ["vendor_id", "ca_type", "ex_date", "ratio", "amount"])
    write("ticker_history", ticker_hist, ["vendor_id", "ticker", "valid_from", "valid_to"])

    print(f"wrote {len(securities)} securities, {len(prices)} price rows, {len(cas)} corporate actions -> {out}")
    if unavailable:
        print("UNAVAILABLE (Yahoo 404 / no data — likely delisted, exposes survivorship gap):")
        for sym, why in unavailable:
            print(f"  {sym}: {why}")


if __name__ == "__main__":
    main()
