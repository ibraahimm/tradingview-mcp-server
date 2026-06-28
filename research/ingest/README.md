# Ingestion — `research/ingest/`

Moves raw vendor/extractor output into the **project-owned, vintage-backed** store, so analysis is
reproducible, portable, and never depends on a mutable user path (e.g. Windows Downloads). Implements
`ARCHITECTURE.md` L1 (immutable vintage dump) + L4 (Parquet panel).

## Flow

```
<source_companies_dir>/*.csv          # the R extractor's output (anywhere)
      │  python -m research.ingest.ingest_tadawul "<source>" [YYYY-MM-DD]
      ▼
research/ingest/raw/tadawul/<vintage>/        immutable copy of the raw CSVs   (gitignored)
      ▼
research/panel/tadawul_<vintage>.parquet      canonical OHLCV frame             (gitignored)
      ▼
research/ingest/manifests/tadawul_<vintage>.json   provenance manifest          (COMMITTED)
```

After ingest, all analysis reads the **vintage Parquet**:

```
python -m research.rigor_run research/panel/tadawul_<vintage>.parquet
python -m research.pipeline   research/panel/tadawul_<vintage>.parquet
```

## What is and isn't committed

| Path | Committed? | Why |
|---|---|---|
| `ingest/raw/tadawul/<vintage>/*.csv` | ❌ gitignored | raw market data (license + size) |
| `panel/tadawul_<vintage>.parquet` | ❌ gitignored | derived data |
| `ingest/manifests/tadawul_<vintage>.json` | ✅ committed | provenance only — no data |
| ingest code + docs | ✅ committed | reproducible pipeline |

## Manifest (provenance) fields

`dataset, vintage, ingested_at_utc, source_path, raw_dir, n_files, n_rows, n_securities,
date_min, date_max, columns, dataset_fingerprint_sha256, parquet_path, parquet_sha256`.

`dataset_fingerprint_sha256` is an order-independent hash of every raw file — re-ingesting the same
data reproduces it, and any change to the underlying data changes it. Every analysis result should
record the `vintage` it ran on, so "which data produced this number?" is always answerable.
