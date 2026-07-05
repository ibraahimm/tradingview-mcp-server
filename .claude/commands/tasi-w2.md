# /tasi-w2 — Saudi Main Market Second-Wave (Continuation) Screen

**Canonical rule:** `TASI-W2` (defined in `research/spec/rules.yaml`). The command name is the lowercase
operational form of the canonical identifier (command rename: `decisions.md` D-2026-07-03-01; identifier
rename: D-2026-07-02-05); the former name /saudi-wave2 is retired.

Find **Saudi Main Market (TADAWUL) only** stocks that keep the `/tasi-w1` **deep
multi-year correction DNA** (still well below the all-time high) but are **one leg further
along**: the **first wave already advanced and held**, the stock **pulled back into a tight
EMA compression**, **reclaimed its short-term EMA**, and is **resuming**. This is the
**second-wave / continuation entry** — strength-after-rest, not a falling knife.

On-demand only. Re-running pulls live data, so the **names change** as the market (or your
parameters) change — the conditions stay fixed.

## Architecture (read first)

This command is **orchestration only**. All exclusions, computed metrics, thresholds, and
table/summary formatting live in a persistent helper that is **not** rebuilt each run:

```
.claude/scripts/tasi-w2.js
```

Each run only (a) fetches live data from the MCP server, (b) pipes it through the script,
and (c) prints what the script returns. Do **not** re-implement the metric math or table
formatting inline. The only files you create are the short-lived JSON under
`.claude/scripts/.tmp/` (deleted at the end) — the script writes the persistent CSV to
`.claude/outputs/tasi-w2.csv`.

> Tool prefix note: calls below use `mcp__tradingview-screener__`. If your MCP server is
> registered under a different name, use that prefix for every tool call.
> Script invocation: the project is ESM (`"type":"module"`), so run with `node …` as shown.

## Why this differs from /tasi-w1 (first wave)

`/tasi-w1` buys the **initial turn** off the multi-year low (far below highs, no moving
averages). `/tasi-w2` buys the **continuation**: the first advance has already happened and
**held**, so it adds a **Stage-2 trend gate (`close > EMA60`)** and a **pullback/coil gate**
(price reclaimed EMA21 without extending, EMA21 compressed near EMA60). The deep-correction
context (`DDmax`/`belowATH`) is **kept** — same universe of corrected names, one wave further
along. TASI-W2's trend/continuation evidence is **structural** (`close > EMA60`, the coil, the
EMA21 reclaim); the former `Perf.1M` band and `Perf.1Y > 0` gates were **removed 2026-07-03**
(`decisions.md` D-2026-07-03-02), then two **lightweight guardrails were restored 2026-07-04**
(D-2026-07-04-01): `Perf.1M < p1m_max` (not overly extended) and `Perf.1Y > py_min` (no severe
1-year weakness — a negative floor, not the old uptrend requirement); `p1m_min` remains removed.
Both guardrails were **widened 2026-07-05** (D-2026-07-05-01) — same predicates, looser bounds.

## Moving averages — EMA only

Per the standing rule, moving averages use **EMA 21 / 60 / 200 only** (no SMA, no other
lengths). The scanner field names are `EMA21`, `EMA60`, `EMA200` (verified present on TADAWUL).
`EMA200` is a **descriptor** (`vs200` column + `★`/`⚠e` tag), **not** a gate — a name recovering
from a deep drop often still has `EMA60 < a falling EMA200`, so requiring `EMA60 > EMA200`
would wrongly exclude legitimate early-second-wave names.

## Parameters

Parse `` for `key=value` tokens. Any key not supplied uses its default. Forward
them straight to the script — the script owns the defaults and all the math.

> **Canonical values live in [`research/spec/rules.yaml`](../../research/spec/rules.yaml)** (rule
> `TASI-W2` → `params`), CI-locked to the script by `methodology_parity.py`; the **change history** is in
> [`research/spec/decisions.md`](../../research/spec/decisions.md). This table documents parameter
> **keys and meaning only — it restates no default values.** For any key the user does not override,
> the script applies the canonical default.

| Key          | Meaning |
|--------------|---------|
| `dd_min`     | Min correction depth `DDmax = (ATH − 52w_low)/ATH` (%) |
| `below_min`  | Min `belowATH = (ATH − close)/ATH` — still corrected / room left (%) |
| `below_max`  | Max `belowATH` — excludes still-wreckage names (%) |
| `offlow`     | Min `offLow = close/52w_low − 1` — first wave already advanced (%) |
| `offlow_max` | Max `offLow` — not over-extended off the low (%) |
| `ema_gap_min`| Min `EMA21/EMA60 − 1` — the coil: fast EMA may sit just below the mid EMA (%) |
| `ema_gap_max`| Max `EMA21/EMA60 − 1` — fast EMA not far above the mid EMA (still coiled) (%) |
| `p1m_max`    | Max `Perf.1M` — guardrail: the recent month not overly extended (no lower band) (%) |
| `p3m_min`    | Min `Perf.3M` (%) |
| `p3m_max`    | Max `Perf.3M` — not overheated (%) |
| `p6m_min`    | Min `Perf.6M` (%) |
| `p6m_max`    | Max `Perf.6M` — only orderly wave-1 advances (%) |
| `py_min`     | Min `Perf.1Y` — guardrail: no severe 1-year weakness (a negative floor, not an uptrend requirement) (%) |
| `p3y_max`    | Max `Perf.3Y` — keep to moderate recoveries (%) |
| `p5y_max`    | Max `Perf.5Y` — allow large recovery (wave 2 wants recovered names) (%) |
| `p10y_max`   | Max `Perf.10Y` (applied locally; null 10Y = <10y history, allowed) (%) |
| `min_years`  | Min years since listing — computed from `first_bar_time`. Younger IPOs excluded |
| `value`      | Min 30-day avg traded value (SAR) liquidity floor; disabled unless set |
| `nrhi_min`   | Optional min `nrHi = close/52w_high` gate (%); descriptor-only unless set |
| `market`     | Fixed scope: Saudi Main Market only (do not change) |

> **`ext21_max` extension cap — removed** (TASI-W2 still requires the reclaim `close ≥ EMA21`; only the
> upper "not-extended" cap is gone). Rationale and validation:
> [`research/spec/decisions.md`](../../research/spec/decisions.md) D-2026-06-30-01.

**Listing age (`min_years`):** enforced via the **direct** field `first_bar_time`
(epoch seconds of the first traded bar ≈ listing date); the script computes
`ageYears = (now − first_bar_time)/yr` and drops anything younger than `min_years`. Do **not**
use `Perf.5Y` existence as the listing proxy — TradingView returns a `Perf.5Y` value even for
sub-5-year listings.

Example calls:
- `/tasi-w2`
- `/tasi-w2 ema_gap_max=8` — widen the coil band for more candidates
- `/tasi-w2 offlow=40 value=5000000` — further along + a SAR 5M liquidity floor
- `/tasi-w2 below_max=80` — restore the pre-2026-07-04 tighter depth ceiling

## Universe restriction (Saudi Main Market only — MANDATORY)

Non-negotiable. **Never substitute symbols from any other market.**
- **Server-side** in `screen_stocks`: `markets:["ksa"]`, `exchange == TADAWUL`, `type == stock`.
- **Locally** the script drops `TADAWUL:9xxx` (Nomu/parallel/ETFs) and any `description`
  matching `REIT|Fund|ETF|Sukuk` (REITs report `type:"stock"` and survive the server filter).
  You do not apply these by hand — the script does.

## Steps

1. **Parse parameters** from `` into `key=value` tokens. Do not compute anything —
   forward the tokens. Map the Perf bounds to the screen filters (below) and the rest to the script.

2. **Run the server-side screen** with `mcp__tradingview-screener__screen_stocks`:
   - `markets: ["ksa"]`
   - `filters`:
     - `{ field:"exchange", operator:"equal", value:"TADAWUL" }`
     - `{ field:"type", operator:"equal", value:"stock" }`
     - `{ field:"Perf.1M", operator:"less", value:<p1m_max> }`  (default 30)
     - `{ field:"Perf.3M", operator:"greater_or_equal", value:<p3m_min> }`  (default 0)
     - `{ field:"Perf.3M", operator:"less", value:<p3m_max> }`  (default 40)
     - `{ field:"Perf.6M", operator:"greater", value:<p6m_min> }`  (default -10)
     - `{ field:"Perf.6M", operator:"less", value:<p6m_max> }`  (default 80)
     - `{ field:"Perf.Y", operator:"greater", value:<py_min> }`  (default -40)
     - `{ field:"Perf.3Y", operator:"less", value:<p3y_max> }`  (default 130)
     - `{ field:"Perf.5Y", operator:"less", value:<p5y_max> }`  (default 200)
     - Do **not** push `Perf.10Y` server-side: `Perf.10Y < p10y_max` is applied **locally** so that
       5–10-year names (null `Perf.10Y`) are kept. Do **not** push the EMA/structure ratios
       (`close>EMA60`, EMA21 reclaim, EMA21/EMA60 coil, DDmax, belowATH, offLow) — the script
       computes and gates them locally so they show up in the funnel.
   - `columns`: `["description","close","all_time_high","price_52_week_high","price_52_week_low","EMA21","EMA60","EMA200","Perf.1M","Perf.3M","Perf.6M","Perf.Y","Perf.3Y","Perf.5Y","Perf.10Y","first_bar_time","average_volume_30d_calc","market_cap_basic","sector"]`
   - The listing-age requirement (`min_years`) is applied **locally** in the script from
     `first_bar_time` — do not push it server-side.
   - `sort_by:"market_cap_basic"`, `sort_order:"desc"`, `limit:200`
   - If `total_count > 200`: re-run in price chunks (`close < 25`, then `close >= 25`) with the
     same filters and merge/de-dupe by symbol before writing the data file.

3. **Write the screen result** verbatim (full JSON with `total_count` and `stocks`) to
   `.claude/scripts/.tmp/screen.json`.

4. **Run the filter stage**, forwarding the parsed params (omit any the user didn't supply):
   ```
   node .claude/scripts/tasi-w2.js stage=filter input=.claude/scripts/.tmp/screen.json \
     dd_min=<dd_min> below_min=<below_min> below_max=<below_max> offlow=<offlow> offlow_max=<offlow_max> \
     ema_gap_min=<ema_gap_min> ema_gap_max=<ema_gap_max> \
     p1m_max=<p1m_max> p3m_min=<p3m_min> p3m_max=<p3m_max> p6m_min=<p6m_min> p6m_max=<p6m_max> \
     py_min=<py_min> p3y_max=<p3y_max> p5y_max=<p5y_max> p10y_max=<p10y_max> min_years=<min_years> value=<value> nrhi_min=<nrhi_min> \
     > .claude/scripts/.tmp/filtered.json
   ```
   The script handles the 9xxx/REIT exclusions, computes all metrics, applies every threshold
   (re-verifying the Perf bounds locally), the missing-field skips, and the sort.

5. **Run the report stage** to produce the table + summary and write the CSV:
   ```
   node .claude/scripts/tasi-w2.js stage=report filtered=.claude/scripts/.tmp/filtered.json
   ```
   The script's stdout has **two parts separated by a line that is exactly `===CHART_LINKS===`**:
   - **Before the sentinel** — a **Funnel block** (base conditions → DDmax → belowATH → offLow →
     trend `close>EMA60` → EMA21 pullback survivors), then the **box-grid table + summary**.
     **Print this whole part as-is inside a fenced ```text code block.** Table columns (fixed order):
     `Sym Name DD% bATH offL nrHi 21g cmp x60 v200 1M 3M 6M 1Y 3Y Cap Sec Tag`, where `21g` =
     `close/EMA21−1`, `cmp` = `EMA21/EMA60−1`, `x60` = `close/EMA60−1`, `v200` = `close/EMA200−1`,
     and **Tag** is `★` when `close > EMA200` (full Stage-2 alignment) or `⚠e` when still below
     EMA200 (early — long downtrend not yet up). Do NOT convert it to a Markdown/ASCII/TSV table
     and do NOT split it.
   - **After the sentinel** — a markdown "**Open chart (click a symbol)**" list (one clickable
     TradingView link per match). **Print as normal markdown OUTSIDE the code block.** Do not
     print the `===CHART_LINKS===` line itself, and do not wrap the links in a code block.
   - If you pass `maxwidth=<N>` and the grid exceeds it, the script prints a WIDTH PROBLEM
     message instead of a broken table — surface that rather than splitting the table.

6. **(Optional) Ingest into the unified tracker** — record this run's survivors into the
   append-only journey ledger BEFORE cleanup deletes the temp file:
   ```
   node .claude/scripts/tasi-track.js stage=ingest filtered=.claude/scripts/.tmp/filtered.json source=TASI-W2
   ```
   Non-fatal: if it errors, surface the message but still finish the run. View the cohort
   anytime with `/tasi-track`. Skip only if the user asked not to track this run.

7. **Clean up** the temp data files only: delete `.claude/scripts/.tmp/`. Do NOT delete the
   persistent script or the CSV in `.claude/outputs/` (the CSV is a deliverable).

## Metric notes & limitations

- **The coil (`EMA21/EMA60`) is the binding gate.** Most steadily-rising names have EMA21 sitting
  well above EMA60; only names that genuinely pulled back to the mid EMA land in `[-2,+5]%`. Expect
  **few hits per run** (often 1–5). Widen `ema_gap_max` for a larger pool.
- **Stage-2 trend uses `close > EMA60` only.** `EMA200` is a descriptor (`vs200`/tag), not a gate —
  see the EMA section above. `★` vs `⚠e` tells you whether the long trend has also turned up.
- **Deep-correction DNA retained.** `DDmax`/`belowATH` keep the universe to names still 20–95% below
  their all-time high — the high `Perf.5Y`/`Perf.10Y` ceilings only permit a large *recovery*, they
  do not admit names at fresh all-time highs. Expect elevated `ATHx` on many hits (old/distant peak);
  that is largely expected for wave 2 — confirm depth on a long-term chart.
- **Listing age uses `first_bar_time`, not `Perf.5Y`.** See the parameters note above.
- **Market cap is converted USD→SAR.** TradingView returns `market_cap_basic` in USD; the script
  multiplies by the SAR/USD peg (3.75) so `Cap` is in SAR, consistent with `close`. (`Val` =
  `avg_volume × close` is already SAR.)
- **No liquidity by default** (`value=0`): pass `value=…` for a tradable cut.
- This command **does not modify the MCP server source**; it relies only on existing tools plus
  the persistent helper in `.claude/scripts/`.
