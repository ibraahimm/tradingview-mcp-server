---
description: Saudi Main Market (TADAWUL) Stage-2 screen — deep multi-year correction (anchored to all-time high) + an extending-but-not-overheated first recovery wave; all thresholds adjustable, incl. Perf.3Y.
---

# /saudi-stage2 — Saudi Main Market Deep-Correction + First-Wave Screen

Find **Saudi Main Market (TADAWUL) only** stocks that suffered a **deep multi-year
correction** (depth anchored to the **all-time high**, not to a fixed 5-year point) and
whose **first recovery wave is underway but not yet overheated**.

On-demand only. Re-running pulls live data, so the **names change** as the market (or your
parameters) change — the conditions stay fixed.

## Architecture (read first)

This command is **orchestration only**. All exclusions, computed metrics, thresholds, and
table/summary formatting live in a persistent helper that is **not** rebuilt each run:

```
.claude/scripts/saudi-stage2.js
```

Each run only (a) fetches live data from the MCP server, (b) pipes it through the script,
and (c) prints what the script returns. Do **not** re-implement the metric math or table
formatting inline. The only files you create are the short-lived JSON under
`.claude/scripts/.tmp/` (deleted at the end) — the script writes the persistent CSV to
`.claude/outputs/saudi-stage2.csv`.

> Tool prefix note: calls below use `mcp__tradingview-screener__`. If your MCP server is
> registered under a different name, use that prefix for every tool call.
> Script invocation: the project is ESM (`"type":"module"`), so run with `node …` as shown.

## Why this differs from /saudi-momentum

`/saudi-momentum` keys off short EMAs (momentum/trend). It **cannot** express "deep
multi-year correction." This command measures **correction depth from the all-time high**
(`DDmax`) so that a peak 7–10 years ago is handled automatically, and demotes point-to-point
`Perf.5Y` to a descriptor (it lies when the peak sits outside its window). See the metric
notes at the bottom.

## Parameters

Parse `$ARGUMENTS` for `key=value` tokens. Any key not supplied uses its default. Forward
them straight to the script — the script owns the defaults and all the math.

| Key         | Default   | Meaning |
|-------------|-----------|---------|
| `dd_min`    | `50`      | Min correction depth `DDmax = (ATH − 52w_low)/ATH` (%) |
| `below_min` | `40`      | Min `belowATH = (ATH − close)/ATH` — still corrected / room left (%) |
| `below_max` | `85`      | Max `belowATH` — excludes the permanently-broken wreckage (%) |
| `offlow`    | `20`      | Min `offLow = close/52w_low − 1` — the recovery wave is underway (%) |
| `p3m_min`   | `5`       | Min `Perf.3M` — a *meaningful* recent turn (%) |
| `p3m_max`   | `40`      | Max `Perf.3M` — not overheated/unconsolidated (%) |
| `p6m_min`   | `-10`     | Min `Perf.6M` — allows fresh turns still slightly negative on 6M (%) |
| `p6m_max`   | `50`      | Max `Perf.6M` — not overextended (%) |
| `p3y_max`   | `130`     | Max `Perf.3Y` — recency-of-correction guard. Lower to `≤20` or `≤0` to purge uptrends (%) |
| `value`     | `0`       | Min 30-day avg traded value (SAR). `0` = OFF (apply liquidity in a later layer) |
| `nrhi_min`  | `0`       | Optional min `nrHi = close/52w_high` strength gate (%). `0` = descriptor only |
| `market`    | `ksa-main`| Fixed scope: Saudi Main Market only (do not change) |

Example calls:
- `/saudi-stage2`
- `/saudi-stage2 p3y_max=20` — purge the uptrend-leaning names (correction-only)
- `/saudi-stage2 p3y_max=0 value=5000000` — strict + a SAR 5M liquidity floor
- `/saudi-stage2 offlow=15 dd_min=60` — wider net, deeper correction

## Universe restriction (Saudi Main Market only — MANDATORY)

Non-negotiable. **Never substitute symbols from any other market.**
- **Server-side** in `screen_stocks`: `markets:["ksa"]`, `exchange == TADAWUL`, `type == stock`.
- **Locally** the script drops `TADAWUL:9xxx` (Nomu/parallel/ETFs) and any `description`
  matching `REIT|Fund|ETF|Sukuk` (REITs report `type:"stock"` and survive the server filter).
  You do not apply these by hand — the script does.

## Steps

1. **Parse parameters** from `$ARGUMENTS` into `key=value` tokens. Do not compute anything —
   forward the tokens. Map them to the screen's Perf bounds (below) and to the script args.

2. **Run the server-side screen** with `mcp__tradingview-screener__screen_stocks`:
   - `markets: ["ksa"]`
   - `filters`:
     - `{ field:"exchange", operator:"equal", value:"TADAWUL" }`
     - `{ field:"type", operator:"equal", value:"stock" }`
     - `{ field:"Perf.3M", operator:"greater_or_equal", value:<p3m_min> }`
     - `{ field:"Perf.3M", operator:"less", value:<p3m_max> }`
     - `{ field:"Perf.6M", operator:"greater", value:<p6m_min> }`
     - `{ field:"Perf.6M", operator:"less", value:<p6m_max> }`
     - `{ field:"Perf.3Y", operator:"less", value:<p3y_max> }`
   - `columns`: `["description","close","all_time_high","price_52_week_high","price_52_week_low","Perf.3M","Perf.6M","Perf.Y","Perf.3Y","Perf.5Y","Perf.10Y","average_volume_30d_calc","market_cap_basic","sector"]`
   - `sort_by:"market_cap_basic"`, `sort_order:"desc"`, `limit:200`
   - If `total_count > 200`: re-run in price chunks (`close < 25`, then `close >= 25`) with the
     same filters and merge/de-dupe by symbol before writing the data file.

   > Do NOT push `DDmax`, `belowATH`, `offLow`, `nrHi`, or `value` to the server — they are
   > ratios the scanner can't filter. The script computes and gates them locally.

3. **Write the screen result** verbatim (full JSON with `total_count` and `stocks`) to
   `.claude/scripts/.tmp/screen.json`.

4. **Run the filter stage**, forwarding the parsed params (omit any the user didn't supply):
   ```
   node .claude/scripts/saudi-stage2.js stage=filter input=.claude/scripts/.tmp/screen.json \
     dd_min=<dd_min> below_min=<below_min> below_max=<below_max> offlow=<offlow> \
     p3m_min=<p3m_min> p3m_max=<p3m_max> p6m_min=<p6m_min> p6m_max=<p6m_max> \
     p3y_max=<p3y_max> value=<value> nrhi_min=<nrhi_min> \
     > .claude/scripts/.tmp/filtered.json
   ```
   The script handles the 9xxx/REIT exclusions, computes all metrics, applies every threshold
   (re-verifying the Perf bounds locally), the missing-field skips, and the sort.

5. **Run the report stage** to produce the table + summary and write the CSV:
   ```
   node .claude/scripts/saudi-stage2.js stage=report filtered=.claude/scripts/.tmp/filtered.json
   ```
   The script's stdout has **two parts separated by a line that is exactly `===CHART_LINKS===`**:
   - **Before the sentinel** — a **Funnel block** (counts after server conditions → DDmax →
     belowATH → offLow → final survivors), then the **box-grid table + summary**. **Print this
     whole part as-is inside a fenced ```text code block.** Table columns (fixed order):
     `Sym Name DD% bATH offL nrHi 3M 6M 1Y 3Y 5Y 10Y ATHx Val Cap Sec Tag`, where **Tag** is
     `★` for `Perf.3Y ≤ 0` (genuine recent correction) and `⚠up` for `Perf.3Y > 0`
     (uptrend-leaning). Do NOT convert it to a Markdown/ASCII/TSV table and do NOT split it.
   - **After the sentinel** — a markdown "**Open chart (click a symbol)**" list (one clickable
     TradingView link per match). **Print as normal markdown OUTSIDE the code block.** Do not
     print the `===CHART_LINKS===` line itself, and do not wrap the links in a code block.
   - If you pass `maxwidth=<N>` and the grid exceeds it, the script prints a WIDTH PROBLEM
     message instead of a broken table — surface that rather than splitting the table.

6. **Clean up** the temp data files only: delete `.claude/scripts/.tmp/`. Do NOT delete the
   persistent script or the CSV in `.claude/outputs/` (the CSV is a deliverable).

## Metric notes & limitations

- **Depth is anchored to the all-time high**, so a peak 7–10 years ago (higher than the
  5-year price) is captured correctly — this is the whole point of `DDmax`/`belowATH` over a
  fixed `Perf.5Y` point, which measures the *recovery*, not the *correction*, when the peak
  predates its window.
- **`ATHx = ATH/52w_high`** flags an old/far peak (e.g. the 2006 TASI bubble). `ATHx ≥ 3` +
  strongly positive `Perf.3Y/10Y` ⇒ a mature uptrend far below an ancient peak, **not** a
  fresh first wave. The script surfaces these in the summary; tighten `p3y_max` to remove them.
- **`Perf.5Y` is a descriptor, not a gate** here — it is unreliable when the peak sits outside
  the 5-year window. Use `Perf.3Y`/`Perf.10Y` together to locate *when* the decline happened.
- **No liquidity by default** (`value=0`): this is a discovery layer. Apply the liquidity +
  moving-average timing as a later, separate layer (or pass `value=…`).
- **ADR/true drawdown caveats:** `52w_low` is a proxy for the cycle trough; a stock that bottomed
  earlier than 52 weeks ago will understate `DDmax`. Confirm depth on a long-term chart.
- This command **does not modify the MCP server source**; it relies only on existing tools plus
  the persistent helper in `.claude/scripts/`.
