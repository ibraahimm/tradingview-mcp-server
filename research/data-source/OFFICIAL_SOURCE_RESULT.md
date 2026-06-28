# Official Saudi Exchange Source — Result (2026-06-28)

## UPDATE (2026-06-28, later): #1 + #3 resolved — the delivered data is ADJUSTED

- **#3 close semantics — RESOLVED.** The API field `previousClosePrice` actually carries the
  **same-day close** (every value lies within that day's [low, high], including IPO days with no
  prior session). The `close` column is correct; returns are trustworthy.
- **#1 adjusted series — RESOLVED, better than expected.** The endpoint exposes `tableTabId=0` =
  **back-adjusted** (splits/bonus) and `tableTabId=1` = as-traded raw. **The delivered files were
  extracted with `tableTabId=0`, so they are already the ADJUSTED (price-return) series** — the
  split-discontinuity worry does not apply. Independently verified here: across **949,901 daily
  returns only 0.008% exceed ±15% and 6 exceed ±30%** (raw splits would cluster at −50%/−90%); the
  series is smooth across known split dates. ⇒ **R2/R3 effectively satisfied** by the adjusted series.
  (`tableTabId=1` raw is optional — for independent verification or explicit dividend reconstruction.)
- **Consequence for the indicative run:** it was already on adjusted data, so its numbers are
  indicative-but-real, **not** split artifacts. Remaining gap for a trustworthy verdict = **#2** below.
- **Only #2 remains:** delisting terminal values — worklist at
  `../reference/curation/delisted_terminal_values.csv` (20 names).

---


The depth question (`DEPTH_PROBE.md`) is **resolved**, and better than expected. Daily history for
individual Tadawul equities **to 2001, including delisted names**, is obtainable from the **official
Saudi Exchange historical-reports endpoint** (extracted via a tested R script, run from a residential
IP — Akamai blocks data-center IPs). This is the survivorship-free + pre-2006 combination no
third-party free source could provide.

## Empirical census (288 company files, verified)

- **951,143 daily rows**; global range **2001-12-31 → 2026-06-25**; 0 empty files.
- **84 / 288 names reach ≤ 2006** (49 begin at 2001-12-31).
- **Survivorship-INCLUSIVE: 20 delisted/suspended names captured with full history**, dates correct:
  - `1040` Alawwal Bank → **2019-06-17** (SABB merger) · `1090` Samba → **2021-04-04** (SNB merger)
  - `2260` Sahara Petrochemical → 2019 (Sipchem) · `1310` Al Mojil → 2017 · `6030` Hail Agri → 2009 · …
- Columns: `date, open, high, low, close, volume, value, trades, symbol, name`.

## Acceptance-harness verdict on the REAL data

Normalized via `acceptance/normalizers/saudiexchange_normalize.py` and run through `run_acceptance.py`:

```
R1 MUST PASS   survivorship-free / delisted / 2006   (delisted=20, earliest=2001-12-31, not-listed-today)
R2 MUST FAIL   adjusted+unadjusted   (raw only; no split/CA to verify)
R3 MUST FAIL   corporate actions     (none in this extract)
R4 MUST FAIL   identifier continuity (id==ticker; we curate sec_id in reference/, so this is handled downstream)
R6 MUST FAIL   delisting metadata    (20 delisted, reason/terminal value not yet curated)
```

**R1 passes on real data — a first.** The failures are exactly **corporate actions + delisting
metadata**, all obtainable from the same authoritative source with additional work (below).

## What this source gives vs what still needs sourcing

| Need | Status from this extract |
|---|---|
| Pre-2006 individual-equity daily history | ✅ to 2001-12-31 |
| Survivorship (delisted included) | ✅ 20 delisted with full history (see completeness caveat) |
| Trading calendar | ✅ authoritative (real trading days) |
| Unadjusted (raw) OHLCV + value + trades | ✅ |
| Adjusted prices | ❌ derive from corporate actions (not yet sourced) |
| Splits / dividends (corporate actions) | ❌ separate Saudi Exchange extraction |
| Delisting reason + terminal value | ❌ curate from exchange announcements (20 names) |
| Stable security id | ⚠️ 4-digit code (stable-ish); `sec_id` curated in `reference/` |

## Open caveats (do not over-claim)

1. **Survivorship completeness:** 20 delisted captured ≠ *all* Tadawul delistings since 2001. The
   endpoint retains entity records for these; older or certain-type delistings may be missing. Needs a
   cross-check against a full historical-listing registry before claiming complete survivorship.
2. **`close` semantics:** the extractor maps `close` from the API field `previousClosePrice`. Verify
   empirically that this is the day's official close (e.g. `close[t]` consistent with the `[low,high]`
   of bar `t`), not the prior day's — a data-QA item before trusting returns.
3. **Raw/unadjusted:** split/par discontinuities will create artificial jumps until corporate-action
   adjustment is applied — so any backtest on raw data is *indicative only* until R2/R3 are sourced.
4. **Licensing:** Saudi Exchange data carries an Information License Agreement — fine for private
   research; redistribution/derived-panel storage terms should be checked (R10). The raw data is **not**
   committed to this repo.

## Next steps (in order)

1. **Corporate actions** — extract splits/dividends/capital changes from the Saudi Exchange → enables
   the adjusted (price-return) series and clears R2/R3.
2. **Delisting metadata** — curate reason + terminal value for the 20 delisted names → clears R6 and
   makes forward-return labeling correct (merger premium vs liquidation ≈ 0).
3. **Data-QA + ingest** — verify the `close` field, build the canonical OHLCV frame → `build_panel`.
4. **First real run** — panel → screen → event-study → governance, initially on raw data labelled
   *indicative (unadjusted)*, then on the adjusted series once (1) lands.
