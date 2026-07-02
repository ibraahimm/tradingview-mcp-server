# /saudi-wave3 — Saudi Main Market Third-Wave (Mature Re-Coil) Screen

**Canonical rule:** `TASI-W3` (defined in `research/spec/rules.yaml`). The command name `/saudi-wave3`
is kept for continuity; the canonical methodology identifier is `TASI-W3` (rename: `decisions.md` D-2026-07-02-05).

Find **Saudi Main Market (TADAWUL) only** stocks **one leg beyond `/saudi-wave2`**: a **mature
uptrend** that already ran its TASI-W1 (first turn off the deep low) and TASI-W2 (first coil + advance),
has climbed back to / near (or made) **new highs**, and is now forming the **NEXT contraction**
— a fresh EMA coil higher up — that sets up the following leg.

Unlike TASI-W1/TASI-W2 this is **not** a "deeply corrected" screen. `DDmax` / `belowATH` / `offLow` are
**descriptors here, not gates** — a TASI-W3 name may be at or near its all-time high. The structure is:
**mature trend (close > EMA200) + the coil again (EMA21≈EMA60, reclaim EMA21) + a pull-back from
a recent high (nrHi band) + a genuine multi-year advance (Perf.3Y/5Y minimums).**

On-demand only. Re-running pulls live data, so the **names change**; the conditions stay fixed.

## Architecture (read first)

Orchestration only. All exclusions, metrics, thresholds, and formatting live in the persistent
helper (not rebuilt each run):

```
.claude/scripts/saudi-wave3.js
```

Each run only (a) fetches live data, (b) pipes it through the script, (c) prints what it returns.
Short-lived JSON goes under `.claude/scripts/.tmp/` (deleted at the end); the script writes the CSV
to `.claude/outputs/saudi-wave3.csv`.

> Tool prefix: `mcp__tradingview-screener__`. Script invocation: ESM, run with `node …`.

## Why this differs from /saudi-wave2

TASI-W2 catches the **first coil** while still deeply corrected (EMA200 only a descriptor, `belowATH`
20–80). TASI-W3 catches the **next contraction in a mature trend**: it **requires** `close > EMA200`,
demotes the deep-correction metrics to descriptors, adds a **pull-back-from-high** gate (`nrHi`),
and — critically — adds **Perf.3Y / Perf.5Y minimums** so only names that delivered a real
multi-year advance qualify (the TASI-W3 discriminator). The coil mechanics (`EMA21/EMA60 ∈ [−2,+5]`,
reclaim `EMA21`, `Perf.1M > 0`) are the same as TASI-W2.

## Moving averages — EMA only

EMA 21 / 60 / 200 only (no SMA). Scanner fields: `EMA21`, `EMA60`, `EMA200`.

## Parameters

Parse `` for `key=value` tokens. Any key not supplied uses its default. Forward to the script.

> **Canonical values live in [`research/spec/rules.yaml`](../../research/spec/rules.yaml)** (rule
> `TASI-W3` → `params`), CI-locked to the script by `methodology_parity.py`. This table documents
> parameter **keys and meaning only — it restates no default values.** For any key the user does not
> override, the script applies the canonical default.

| Key | Meaning |
|-----|---------|
| `vs200_min` | Min `close/EMA200 − 1` — **gate**: close above EMA200 (mature trend) (%) |
| `ema_gap_min` / `ema_gap_max` | The coil: `EMA21/EMA60 − 1` band (%) |
| `ext21_max` | Max `close/EMA21 − 1` — reclaimed EMA21 but not extended (%) |
| `nrhi_min` / `nrhi_max` | `close/52w_high` band — pulled back from a recent high (%) |
| `p1m_min` / `p1m_max` | `Perf.1M` — turning up out of the coil, not vertical (%) |
| `p3m_min` / `p3m_max` | `Perf.3M` — recent contraction = modest (%) |
| `p6m_min` / `p6m_max` | `Perf.6M` (%) |
| `py_min` / `py_max` | `Perf.1Y` (%) |
| `p3y_min` / `p3y_max` | **`Perf.3Y` band — the min is the primary TASI-W3 discriminator** (%) |
| `p5y_min` / `p5y_max` | `Perf.5Y` band — softer min (5Y less reliable when peak predates window) (%) |
| `p10y_max` | Max `Perf.10Y` (applied locally; null = <10y history, allowed) (%) |
| `min_years` | Min years since listing (from `first_bar_time`) |
| `value` | Min 30-day avg traded value (SAR) liquidity floor; disabled unless set |
| `market` | Fixed scope (do not change) |

`DDmax` / `belowATH` / `offLow` have **no gate parameters** — computed and shown as descriptors only.

Example calls:
- `/saudi-wave3`
- `/saudi-wave3 p3y_min=80` — stricter "must be a big multi-year winner"
- `/saudi-wave3 nrhi_max=100` — include names sitting right at new highs
- `/saudi-wave3 value=5000000` — add a SAR 5M liquidity floor

## Universe restriction (Saudi Main Market only — MANDATORY)

- **Server-side**: `markets:["ksa"]`, `exchange == TADAWUL`, `type == stock`.
- **Locally** the script drops `TADAWUL:9xxx` and `REIT|Fund|ETF|Sukuk` descriptions. Do not apply by hand.

## Steps

1. **Parse parameters** from `` into `key=value` tokens.

2. **Run the server-side screen** with `mcp__tradingview-screener__screen_stocks`:
   - `markets: ["ksa"]`
   - `filters`:
     - `{ field:"exchange", operator:"equal", value:"TADAWUL" }`
     - `{ field:"type", operator:"equal", value:"stock" }`
     - `{ field:"Perf.1M", operator:"greater", value:<p1m_min> }` and `{ ...operator:"less", value:<p1m_max> }`
     - `{ field:"Perf.3M", operator:"greater_or_equal", value:<p3m_min> }` and `{ ...operator:"less", value:<p3m_max> }`
     - `{ field:"Perf.6M", operator:"greater", value:<p6m_min> }` and `{ ...operator:"less", value:<p6m_max> }`
     - `{ field:"Perf.Y", operator:"greater", value:<py_min> }` and `{ ...operator:"less", value:<py_max> }`
     - `{ field:"Perf.3Y", operator:"greater_or_equal", value:<p3y_min> }` and `{ ...operator:"less", value:<p3y_max> }`
     - `{ field:"Perf.5Y", operator:"greater_or_equal", value:<p5y_min> }` and `{ ...operator:"less", value:<p5y_max> }`
     - Do **not** push `Perf.10Y` (local, null-preserving) or the EMA/structure ratios (`close>EMA200`,
       the coil, `nrHi`) — the script computes/gates those locally so they appear in the funnel.
   - `columns`: `["description","close","all_time_high","price_52_week_high","price_52_week_low","EMA21","EMA60","EMA200","Perf.1M","Perf.3M","Perf.6M","Perf.Y","Perf.3Y","Perf.5Y","Perf.10Y","first_bar_time","average_volume_30d_calc","market_cap_basic","sector"]`
   - `sort_by:"market_cap_basic"`, `sort_order:"desc"`, `limit:200`
   - If `total_count > 200`: re-run in price chunks (`close < 25`, then `close >= 25`) and merge/de-dupe.

3. **Write the screen result** verbatim to `.claude/scripts/.tmp/screen.json`.

4. **Run the filter stage** (omit any param the user didn't supply):
   ```
   node .claude/scripts/saudi-wave3.js stage=filter input=.claude/scripts/.tmp/screen.json \
     vs200_min=<vs200_min> ema_gap_min=<ema_gap_min> ema_gap_max=<ema_gap_max> ext21_max=<ext21_max> \
     nrhi_min=<nrhi_min> nrhi_max=<nrhi_max> p1m_min=<p1m_min> p1m_max=<p1m_max> p3m_min=<p3m_min> p3m_max=<p3m_max> \
     p6m_min=<p6m_min> p6m_max=<p6m_max> py_min=<py_min> py_max=<py_max> p3y_min=<p3y_min> p3y_max=<p3y_max> \
     p5y_min=<p5y_min> p5y_max=<p5y_max> p10y_max=<p10y_max> min_years=<min_years> value=<value> \
     > .claude/scripts/.tmp/filtered.json
   ```

5. **Run the report stage**:
   ```
   node .claude/scripts/saudi-wave3.js stage=report filtered=.claude/scripts/.tmp/filtered.json
   ```
   Stdout has **two parts split by a line that is exactly `===CHART_LINKS===`**:
   - **Before the sentinel** — Funnel (base → trend → mature(EMA200) → coil → nrHi survivors), then the
     **box-grid table + summary**. **Print as-is inside a fenced ```text code block.** Columns (fixed):
     `Sym Name DD% bATH offL nrHi 21g cmp x60 v200 1M 3M 6M 1Y 3Y 5Y Cap Sec Tag`. **Tag** is `★` when
     `belowATH < 10` (at/near new highs) or `↑` (still climbing). Do NOT convert/split the table.
   - **After the sentinel** — a markdown "**Open chart (click a symbol)**" list, printed OUTSIDE the
     code block. Do not print the sentinel line itself.
   - If `maxwidth=<N>` is exceeded the script prints a WIDTH PROBLEM message — surface it.

6. **(Optional) Ingest into the unified tracker** — record this run's survivors BEFORE cleanup:
   ```
   node .claude/scripts/saudi-tracker.js stage=ingest filtered=.claude/scripts/.tmp/filtered.json source=TASI-W3
   ```
   Non-fatal: if it errors, surface the message but still finish. View the cohort with `/saudi-track`.
   Skip only if the user asked not to track this run.

7. **Clean up** the temp data files only: delete `.claude/scripts/.tmp/`. Do NOT delete the persistent
   script or the CSV in `.claude/outputs/`.

## Metric notes & limitations

- **Not a corrected screen.** `belowATH ≈ 0` ⇒ at/near new highs (allowed). The deep-correction
  metrics are descriptors; TASI-W3 is a *mature re-coil*.
- **`Perf.3Y` minimum is the discriminator.** It separates TASI-W3 (genuine multi-year winner re-coiling)
  from a name that merely sits above EMA200. `Perf.5Y` min is softer — 5Y is unreliable when the peak
  predates its window (same caveat as TASI-W1/TASI-W2 depth).
- **The coil is the binding gate.** `EMA21/EMA60 ∈ [−2,+5]` plus the `nrHi` pull-back band is tight;
  expect few hits per run. Widen `ema_gap_max` / `nrhi_min` for a larger pool.
- **Market cap USD→SAR** via the 3.75 peg (as in TASI-W1/TASI-W2).
- Relies only on existing MCP tools plus the persistent helper; does not modify the server source.
