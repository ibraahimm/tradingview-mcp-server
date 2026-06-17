---
description: Saudi Main Market (TADAWUL) momentum/trend screen — rise from 52-week low + EMA alignment + ADR & liquidity filters, all parameters adjustable
---

# /saudi-momentum — Saudi Main Market Momentum Screen

Screen the **Saudi Main Market (TADAWUL) only** for stocks that are rising off their
52-week low while in a confirmed-but-tight uptrend (EMA fast just above EMA slow,
price above EMA slow), with minimum daily range (ADR) and minimum traded liquidity.

On-demand only. Re-running pulls live data, so the **stock names change as the market
(or your parameters) change** — the conditions stay fixed.

## Architecture (read first)

This command is **orchestration only**. All local exclusions, computed filters, and
table/summary formatting live in a persistent helper script that is **not** rebuilt on
each run:

```
.claude/scripts/saudi-momentum.js
```

Each run only (a) fetches live data from the MCP server, (b) pipes it through the
script, and (c) prints what the script returns. Do **not** re-implement the filter math
or table formatting inline, and do **not** create ad-hoc throwaway logic files. The only
files you create are the short-lived JSON data files under `.claude/scripts/.tmp/` (which
you delete at the end) — the script itself writes the persistent CSV deliverable to
`.claude/outputs/saudi-momentum.csv`.

> Tool prefix note: the calls below use the `mcp__tradingview-screener__` prefix. If your
> MCP server is registered under a different name (e.g. `mcp__tradingview__`), use that
> prefix instead for every tool call.

> Script invocation note: the project is an ESM package (`"type": "module"`), so run the
> helper with `node .claude/scripts/saudi-momentum.js …` exactly as shown (it is ESM).

## Parameters

Parse `$ARGUMENTS` for `key=value` tokens. Any key not supplied uses its default. Pass
them straight through to the script as `key=value` args — the script owns the defaults.

| Key         | Default     | Meaning |
|-------------|-------------|---------|
| `gain`      | `40`        | Min % rise above the 52-week low |
| `ema_fast`  | `21`        | Fast EMA period |
| `ema_slow`  | `60`        | Slow EMA period |
| `spread`    | `5`         | Max % the fast EMA may sit above the slow EMA |
| `adr`       | `1`         | Min ADR % (Average Daily Range proxy = ATR ÷ close) |
| `value`     | `5000000`   | Min 30-day average traded value, in SAR |
| `market`    | `ksa-main`  | Fixed scope: Saudi Main Market only (do not change) |

Example calls:
- `/saudi-momentum`
- `/saudi-momentum gain=50 spread=4 adr=1.2 value=10000000`
- `/saudi-momentum gain=60 ema_fast=20 ema_slow=50`

Build the dynamic EMA column names from the params: `EMA{ema_fast}` and `EMA{ema_slow}`
(e.g. defaults → `EMA21`, `EMA60`). These non-standard periods are accepted by the API.

## Universe restriction (Saudi Main Market only — MANDATORY)

These rules are non-negotiable. **Never substitute symbols from any other market.**

- **Server-side**, in the `screen_stocks` call:
  - `markets: ["ksa"]`
  - filter `{ field: "exchange", operator: "equal", value: "TADAWUL" }`
  - filter `{ field: "type", operator: "equal", value: "stock" }` (drops ETFs/funds, which report `type:"fund"`)
- **Locally**, the helper script drops any row where the numeric code starts with `9`
  (`TADAWUL:9xxx` = Nomu / parallel market / ETFs) or the `description` matches (case-
  insensitive) `REIT`, `Fund`, `ETF`, or `Sukuk` (REITs report `type:"stock"` and survive
  the server filter). You do not apply these by hand — the script does.

## Steps

1. **Parse parameters** from `$ARGUMENTS` into `key=value` tokens. You do not convert
   percents or compute anything — the script does. Keep the tokens to forward.

2. **Run the server-side screen** with `mcp__tradingview-screener__screen_stocks`:
   - `markets: ["ksa"]`
   - `filters`:
     - `{ field: "exchange", operator: "equal", value: "TADAWUL" }`
     - `{ field: "type", operator: "equal", value: "stock" }`
     - `{ field: "close", operator: "greater", value: "EMA{ema_slow}" }`  ← price > slow EMA
     - `{ field: "EMA{ema_fast}", operator: "greater", value: "EMA{ema_slow}" }`  ← fast EMA > slow EMA
   - `columns`: `["description", "close", "price_52_week_low", "EMA{ema_fast}", "EMA{ema_slow}", "ATR", "average_volume_30d_calc"]`
     (the minimum needed for the computed conditions; the EMA values feed `ema_spread` and are NOT displayed)
   - `sort_by: "market_cap_basic"`, `sort_order: "desc"`, `limit: 200`
   - If `total_count > 200`: re-run in price chunks (`close < 25`, then `close >= 25`) with
     the same filters and merge/de-dupe by symbol before writing the data file. (With
     defaults the filtered set is well under 200.)

   > Do NOT use the `above_percent` operator for `gain` or `spread` — it is broken for
   > thresholds ≥ ~10 (returns 0). These conditions are computed in the script instead.

3. **Write the screen result** verbatim (the full JSON object with `total_count` and
   `stocks`) to a temp data file, e.g. `.claude/scripts/.tmp/screen.json`.

4. **Run the filter stage** of the script, forwarding the parsed params:
   ```
   node .claude/scripts/saudi-momentum.js stage=filter input=.claude/scripts/.tmp/screen.json \
     gain=<gain> ema_fast=<ema_fast> ema_slow=<ema_slow> spread=<spread> adr=<adr> value=<value> \
     > .claude/scripts/.tmp/filtered.json
   ```
   Omit any param the user didn't supply (the script applies its own defaults). The
   script handles the 9xxx/REIT exclusions, all computed conditions, the missing-field
   skips, and the sort. Read `.tmp/filtered.json` to get `matches[].symbol`.

5. **Fetch display fields for survivors only** with `mcp__tradingview-screener__lookup_symbols`
   for exactly the `matches[].symbol` list:
   `["description", "change", "volume", "relative_volume_10d_calc", "Perf.3M", "Perf.Y", "Perf.5Y", "Perf.10Y", "Perf.All", "average_volume_30d_calc", "market_cap_basic", "sector"]`.
   Write the lookup result verbatim to `.claude/scripts/.tmp/lookup.json`.
   (If `matches` is empty, skip the lookup and run the report stage with an empty
   `{"symbols":[]}` lookup file so it prints the header + "No matches".)

6. **Run the report stage** to produce the final drawn-grid table + summary and write the CSV:
   ```
   node .claude/scripts/saudi-momentum.js stage=report \
     filtered=.claude/scripts/.tmp/filtered.json lookup=.claude/scripts/.tmp/lookup.json
   ```
   The script's stdout has **two parts separated by a line that is exactly `===CHART_LINKS===`**:
   - **Before the sentinel** — the box-grid table + summary. **Print this part as-is, inside a
     fenced ```text code block** so the box-drawing alignment is preserved. The script emits
     **one continuous box-grid table** (Unicode `┌┬┐ ├┼┤ └┴┘ │ ─`) — short column headers
     (`Sym Name Close Chg Vol RVol Val Low% Sprd ADR 3M 1Y 5Y 10Y All Cap Sec`), one stock per
     row, all 17 columns, with the `TADAWUL:` prefix stripped and long Company/Sector names
     truncated — followed by the short summary (matches, strongest 3, liquidity warnings,
     missing-data warnings, Saudi-Main-Market-only scope, CSV path). Do NOT convert this part
     to a Markdown pipe table, a `+---+` ASCII table, TSV, or per-stock blocks, and do NOT
     split the table — print it verbatim.
   - **After the sentinel** — a markdown "**Open chart (click a symbol)**" list, one clickable
     TradingView link per match. **Print this part as normal markdown OUTSIDE the code block**
     (links do not render inside a ```text fence). Do **not** print the `===CHART_LINKS===`
     line itself, and do **not** wrap the links in a code block.

   The script also writes the **full, untruncated** results as a CSV to
   `.claude/outputs/saudi-momentum.csv` (override with `csv=<path>`).
   - The grid is ~140–150 characters wide (17 columns). It renders cleanly as fixed-width
     text but needs a wide terminal. If you pass `maxwidth=<N>` and the grid exceeds it, the
     script prints a WIDTH PROBLEM message instead of a wrapped table and points to the CSV;
     surface that to the user rather than splitting the table on your own.

7. **Clean up** the temp *data* files only: delete `.claude/scripts/.tmp/` (or the
   individual `screen.json`, `filtered.json`, `lookup.json`). Do NOT delete the persistent
   script or the CSV in `.claude/outputs/` — the CSV is a deliverable the user keeps.

## Notes & limitations

- **ADR is a proxy.** The API has no Average Daily Range field, so `adr_pct = ATR(14) / close`.
  True ADR (mean of daily High−Low) is usually slightly lower than ATR%, so names near the
  `adr` threshold are worth confirming on a chart.
- **No traded-value field.** `avg_value` is computed as `average_volume_30d_calc × close`.
  A high-priced, low-volume stock can clear the value floor while still being thin — the
  script flags these in the liquidity warnings.
- **EMA periods 21/60 are non-standard** but are accepted by the scanner API. Other periods
  also work; change `ema_fast`/`ema_slow` freely (the script reads the matching `EMA{n}` columns).
- **`above_percent` is unreliable** for thresholds ≥ ~10 — that is why `gain` and `spread`
  are computed in the script rather than pushed to the server.
- This command **does not modify the MCP server source**; it relies only on existing tools
  plus the persistent helper script in `.claude/scripts/`.
