#!/usr/bin/env python3
"""Normalize the Saudi Exchange (Tadawul) official-extractor output into the acceptance-harness
sample contract (see ../README.md). Reads the per-company CSVs produced by the R extractor
(columns: date,open,high,low,close,volume,value,trades,symbol,name) and writes the four sample
tables.

    python saudiexchange_normalize.py <companies_dir> <out_dir>

Mapping / honest limitations of this source:
  vendor_id  = symbol           (the 4-digit code; no stable surrogate -> R4 gap, curated downstream)
  close_unadj= close, adj_factor= 1.0   (source is RAW/unadjusted; no adjusted series exists)
  corporate_actions = EMPTY      (this extract has no splits/dividends -> R2/R3 will flag)
  delist_date = last bar date when it is well before today (survivorship-INCLUSIVE: delisted names
                are present with full history); delist_reason/terminal_value unknown -> R6 will flag.
"""
from __future__ import annotations
import csv, glob, os, sys

TODAY_CUT = "2026-06-01"   # last bar before this => not currently trading (delisted/suspended)


def main(companies_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(companies_dir, "*.csv")))
    securities, ticker_hist = [], []
    n_delisted = 0
    with open(os.path.join(out_dir, "prices.csv"), "w", newline="") as pf:
        pw = csv.writer(pf)
        pw.writerow(["vendor_id", "date", "open", "high", "low", "close", "close_unadj", "adj_factor", "volume"])
        for f in files:
            sym = os.path.splitext(os.path.basename(f))[0]
            d = list(csv.DictReader(open(f, encoding="utf-8-sig")))
            ds = sorted(r["date"] for r in d if r.get("date"))
            if not ds:
                continue
            first, last = ds[0], ds[-1]
            name = d[0].get("name", "")
            delist = last if last < TODAY_CUT else ""
            if delist:
                n_delisted += 1
            securities.append(dict(vendor_id=sym, ticker=sym, name=name, list_date=first,
                                   delist_date=delist, delist_reason="", terminal_value=""))
            ticker_hist.append(dict(vendor_id=sym, ticker=sym, valid_from=first, valid_to=""))
            for r in d:
                c = r.get("close", "")
                pw.writerow([sym, r.get("date", ""), r.get("open", ""), r.get("high", ""),
                             r.get("low", ""), c, c, "1.0" if c else "", r.get("volume", "")])

    with open(os.path.join(out_dir, "securities.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["vendor_id", "ticker", "name", "list_date", "delist_date", "delist_reason", "terminal_value"])
        w.writeheader(); w.writerows(securities)
    with open(os.path.join(out_dir, "ticker_history.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["vendor_id", "ticker", "valid_from", "valid_to"])
        w.writeheader(); w.writerows(ticker_hist)
    with open(os.path.join(out_dir, "corporate_actions.csv"), "w", newline="") as f:
        csv.writer(f).writerow(["vendor_id", "ca_type", "ex_date", "ratio", "amount"])  # none in this extract

    print(f"normalized {len(securities)} securities ({n_delisted} delisted/suspended) -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
