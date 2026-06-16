# Saudi Main Market Command Registry

Reusable Claude Code slash commands scoped to the **Saudi Main Market (TADAWUL) only**.
All commands are **on-demand** (no scheduling) and pull live data on each run, so only the
matching stock names change as the market or your parameters change — the logic and the
output format stay fixed.

**Universe restriction (applies to every command here):**
- TADAWUL main-market listed **stocks** only; symbols are never substituted from other markets.
- Excluded: Nomu / parallel-market `9xxx` symbols, ETFs, and REITs/funds when identifiable
  (matched by `REIT`/`Fund`/`ETF`/`Sukuk` in the description, since they report
  `type:"stock"` and survive the server-side filter).

Command files live in [`.claude/commands/`](../.claude/commands/). To add a new command,
create `.claude/commands/<name>.md` (frontmatter `description:` + instructions) and append a
section to this registry following the template at the bottom.

---

## `/saudi-momentum`

**Type:** On-demand Claude Code slash command. Scope: Saudi Main Market (TADAWUL) only
(see the universe restriction above).

**Purpose:** Find Saudi main-market stocks rising off their 52-week low while in a
confirmed-but-tight uptrend (fast EMA just above slow EMA, price above slow EMA), with a
minimum daily range (ADR) and minimum traded liquidity.

**Persistent implementation files:**
- `.claude/commands/saudi-momentum.md` — orchestration (fetches live MCP data, pipes it
  through the helper script, prints the result).
- `.claude/scripts/saudi-momentum.js` — persistent helper that owns the local exclusions,
  the computed filters, and the fixed report formatting (not rebuilt on each run).

**Parameterized — call with defaults or custom values:**

| Key        | Default    | Meaning |
|------------|------------|---------|
| `gain`     | `40`       | Min % rise above 52-week low |
| `ema_fast` | `21`       | Fast EMA period |
| `ema_slow` | `60`       | Slow EMA period |
| `spread`   | `5`        | Max % the fast EMA may sit above the slow EMA |
| `adr`      | `1`        | Min ADR % (ATR ÷ close proxy) |
| `value`    | `5000000`  | Min 30-day average traded value (SAR) |
| `market`   | `ksa-main` | Fixed scope — Saudi Main Market / TADAWUL only (do not change) |

`market` is fixed; the other six parameters are editable.

**Example calls:**
- `/saudi-momentum`
- `/saudi-momentum gain=50 spread=4 adr=1.2 value=10000000`

**Logic (conditions):**
- `gain_from_low = (close / price_52_week_low) - 1` ≥ `gain`
- `close > EMA{ema_slow}`
- `EMA{ema_fast} > EMA{ema_slow}`
- `ema_spread = (EMA{ema_fast} / EMA{ema_slow} - 1)` ≤ `spread`
- `adr_pct = ATR / close` ≥ `adr`
- `avg_value = average_volume_30d_calc * close` ≥ `value`
- Sort by `gain_from_low` descending.

**Screen output — fixed drawn grid table.** One continuous box-drawing grid table (Unicode
`┌┬┐ ├┼┤ └┴┘ │ ─`): one header row, one stock per row, continuous borders, vertical column
separators, and a header/data rule — not a Markdown table, not TSV, not split into per-stock
blocks. To fit all 17 columns on one screen the grid uses **short headers**, strips the
`TADAWUL:` symbol prefix, truncates long company/sector names, and uses compact numbers.

Short headers, in order:

```
Sym · Name · Close · Chg · Vol · RVol · Val · Low% · Sprd · ADR · 3M · 1Y · 5Y · 10Y · All · Cap · Sec
```

Meaning: Sym = symbol (TADAWUL code) · Name = company · Close · Chg = daily change % ·
Vol = today's volume · RVol = relative volume (10-day) · Val = avg traded value (SAR) ·
Low% = gain from 52-week low · Sprd = EMA spread % · ADR = ADR % (ATR/close) ·
3M/1Y/5Y/10Y/All = performance · Cap = market cap · Sec = sector.

**CSV output (full, untruncated):** the same results are written to
`.claude/outputs/saudi-momentum.csv` (UTF-8 with BOM, Excel-friendly), keeping full values —
full `TADAWUL:` symbols, full company/sector names, signed `+xx.x%` / `SAR xx.xM` — under the
long column headers. Override the path with `csv=<path>` on the report stage.

**Summary (printed after the grid):** match count · strongest 3 names · liquidity warnings ·
missing-data warnings · Saudi Main Market scope confirmation · CSV file path.

**Notes & limitations:**
- **ADR is a proxy** (`ATR(14)/close`); true ADR is usually slightly lower — confirm
  borderline names on a chart.
- **No traded-value field** — `avg_value` = `average_volume_30d_calc × close`; high-priced
  thin names can clear the floor (flagged as a liquidity warning).
- `above_percent` is **not** used for `gain`/`spread` (broken for thresholds ≥ ~10); both are
  computed locally in the helper script.
- Server-side conditions: `market`/`exchange`/`type`, `close > EMA{slow}`,
  `EMA{fast} > EMA{slow}`. The 9xxx/REIT-fund exclusions and everything else are computed locally.
- The grid is ~140–150 characters wide (17 columns); it renders cleanly as fixed-width text
  but needs a wide terminal, and is never split unless you explicitly approve it.

---

## Template for new commands

```
## /<command-name>

**Type:** On-demand Claude Code slash command. Scope: Saudi Main Market (TADAWUL) only.
**Purpose:** <one line>
**Persistent implementation files:**
  - `.claude/commands/<command-name>.md`
  - `.claude/scripts/<command-name>.js` (if it uses a helper script)
**Parameterized — call with defaults or custom values:** <table>
**Example calls:** <list>
**Logic (conditions):** <list>
**Screen output:** <fixed format description>
**CSV output:** `.claude/outputs/<command-name>.csv` (full, untruncated)
**Summary:** <list>
**Notes & limitations:** <list>
```

> Pending: more Saudi-scoped commands will be added here on request. Do not build the next
> command until its rules are provided.
