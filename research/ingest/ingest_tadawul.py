#!/usr/bin/env python3
"""Ingest the Saudi Exchange extractor output into the project-owned, vintage-backed store.

    python -m research.ingest.ingest_tadawul "<source_companies_dir>" [vintage=YYYY-MM-DD]

Flow (see ../ARCHITECTURE.md L1/L4 — immutable vintage dump + Parquet panel):

    <source>/*.csv
        -> research/ingest/raw/tadawul/<vintage>/   (immutable copy; gitignored)
        -> research/panel/tadawul_<vintage>.parquet  (canonical OHLCV frame; gitignored)
        -> research/ingest/manifests/tadawul_<vintage>.json  (provenance; COMMITTED, no data)

After this, pipeline.py / rigor_run.py read the Parquet by vintage — never the Downloads path.
Raw CSVs and Parquet are gitignored; only the manifest (counts/hashes/paths) is committed.
"""
from __future__ import annotations
import datetime
import glob
import hashlib
import json
import os
import shutil
import sys

import polars as pl

sys.path.insert(0, os.getcwd())
from research.pipeline import load   # noqa: E402

RAW_ROOT = "research/ingest/raw/tadawul"
PANEL_DIR = "research/panel"
MANIFEST_DIR = "research/ingest/manifests"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    src = sys.argv[1]
    vintage = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().isoformat()
    raw_dir = os.path.join(RAW_ROOT, vintage)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(PANEL_DIR, exist_ok=True)
    os.makedirs(MANIFEST_DIR, exist_ok=True)

    src_files = sorted(glob.glob(os.path.join(src, "*.csv")))
    if not src_files:
        raise SystemExit(f"no *.csv found in {src!r}")
    print(f">> copying {len(src_files)} files -> {raw_dir} (immutable raw dump)")
    file_hashes = []
    for f in src_files:
        dst = os.path.join(raw_dir, os.path.basename(f))
        shutil.copy2(f, dst)
        file_hashes.append(_sha256(dst))
    fingerprint = hashlib.sha256("".join(sorted(file_hashes)).encode()).hexdigest()

    print(">> materializing canonical OHLCV Parquet ...")
    prices = load(raw_dir)                       # clean canonical frame (sec_id,date,ohlcv)
    pq = os.path.join(PANEL_DIR, f"tadawul_{vintage}.parquet")
    prices.write_parquet(pq)

    manifest = {
        "dataset": "tadawul",
        "vintage": vintage,
        "ingested_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_path": os.path.abspath(src),
        "raw_dir": raw_dir,
        "n_files": len(src_files),
        "n_rows": prices.height,
        "n_securities": int(prices["sec_id"].n_unique()),
        "date_min": str(prices["date"].min()),
        "date_max": str(prices["date"].max()),
        "columns": prices.columns,
        "dataset_fingerprint_sha256": fingerprint,   # order-independent hash of all raw files
        "parquet_path": pq,
        "parquet_sha256": _sha256(pq),
    }
    mpath = os.path.join(MANIFEST_DIR, f"tadawul_{vintage}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f">> ingested vintage {vintage}: {manifest['n_files']} files, {manifest['n_rows']:,} rows, "
          f"{manifest['n_securities']} securities, {manifest['date_min']}->{manifest['date_max']}")
    print(f"   parquet : {pq}")
    print(f"   manifest: {mpath}  (fingerprint {fingerprint[:16]}...)")
    print(f"\nRun analysis from the vintage Parquet:\n   python -m research.rigor_run {pq}")


if __name__ == "__main__":
    main()
