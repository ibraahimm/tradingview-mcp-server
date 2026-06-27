# Vendor Evaluation — Historical Tadawul Data

**Status:** Draft v0.1 · 2026-06-27 · evidence-graded, requirements-driven (`REQUIREMENTS.md`).

Evaluates candidate sources against the MUST gates for a **survivorship-free, corporate-action-aware**
Tadawul backtest. Grading is explicit about evidence:

- **✅ confirmed** — stated in the vendor's own docs / authoritative source (cited).
- **🟡 likely** — strongly implied by general capability, not Saudi-specifically confirmed.
- **❓ unknown** — not determinable from public info; **requires trial / direct confirmation**.
- **❌ likely-fails** — evidence indicates it does not meet the requirement.

> Bottom line up front: **no affordable API is *confirmed* to provide delisted Saudi equity prices back
> through 2006** (the single gating MUST, R1). Enterprise feeds (LSEG/Bloomberg) almost certainly do but
> cost/licensing is the friction. So the decision is **trial-gated**, and the acceptance harness exists
> to resolve R1 objectively on sample data before any commitment.

## The gating requirement

Everything hinges on **R1 (survivorship-free + delisted + 2006 depth)**. Adjusted/unadjusted (R2),
corporate actions (R3), identifiers (R4) are table-stakes most serious vendors meet. The thing that
eliminates most affordable options is **delisted Saudi names with price history back to the 2006 cycle**.

## Per-candidate assessment (vs MUST gates)

| Vendor | R1 delisted+2006 | R2 adj+unadj | R3 corp actions | R4 identifiers | R5 calendar | R6 delist meta | R7 reconcilable | R10 license (derived storage) |
|---|---|---|---|---|---|---|---|---|
| **EODHD** | ❓ **crux** (US delisted ✅; Saudi delisted undocumented) | ✅ raw OHLC + adjusted_close | ✅ splits/divs | 🟡 | 🟡 | ❓ | ✅ (identifiable) | ❓ confirm derived-panel terms |
| **LSEG Datastream / Workspace** | 🟡 (deep delisted+PIT is its core; Saudi-specific unconfirmed) | 🟡 | ✅ | ✅ | ✅ | 🟡 | ✅ | ❓ enterprise contract; cost high |
| **SAHMK** (Tadawul-licensed, local) | ❓ (350+ TASI+Nomu live; delisted/2006 unknown) | ❓ | 🟡 (dividends ✅) | 🟡 | ✅ (local) | ❓ | ✅ | 🟡 Tadawul-licensed — clearest license path |
| **Twelve Data** | ❌ likely (recent-focused; delisted not advertised; splits "last 10+y") | ❓ (adjusted ✅; raw?) | 🟡 splits/divs | 🟡 | 🟡 | ❌ | ✅ (good 2nd source) | 🟡 |
| **Finnhub** | ❌ likely (recent/real-time focus; Saudi history premium; delisted not a strength) | ❓ | 🟡 | 🟡 | ❓ | ❌ | 🟡 | 🟡 |
| **Saudi Exchange (official EOD)** | ❌ **EOD only last 5 years, listed-only** | ❓ | 🟡 | ✅ (authoritative) | ✅ (authoritative) | 🟡 (eReference) | ✅ | ❓ Information License Agreement |
| **Argaam / Mubasher** | ❌ as a price API; ✅ as a *reference* source for delisting/CA facts | n/a | 🟡 (events/CA) | n/a | n/a | 🟡 (filings) | n/a | ❓ |
| **Bloomberg / FactSet / ICE** | 🟡 (enterprise-grade; very likely) | 🟡 | ✅ | ✅ | ✅ | 🟡 | ✅ | ❓ enterprise; cost high |

### Notes & evidence per candidate

**EODHD** — *best affordable candidate, one gating unknown.*
- ✅ Non-US exchanges covered **mostly from 2000-01-03** → 2006 depth is in scope.
- ✅ Returns **raw OHLC (unadjusted) + `adjusted_close` + volume** — satisfies R2 at the close level
  (note: only *close* is adjusted; adjusted high/low not provided → a small 52w-H/L fidelity caveat).
- ✅ Splits/dividends endpoints; `adjusted_close` reflects them (R3 plausible — completeness for Saudi to verify).
- ❓ **Delisted coverage is documented for the US (~11,000 names since 2000); Saudi `.SR` delisted is NOT
  documented.** This is the crux — must be confirmed on a trial (R1).
- ❓ License terms for storing a derived panel — confirm (R10).

**LSEG Datastream / Workspace (ex-Refinitiv)** — *the fidelity-safe bet; cost is the friction.*
- 🟡 120+ years, 175 countries, deep delisted + point-in-time is its defining strength → Saudi delisted
  PIT is very likely present, but not Saudi-specifically confirmed in public docs.
- Enterprise license, academic/seat-based access; R10 derived-storage terms need negotiation; cost high
  for a single-market price-only use.

**SAHMK** — *Saudi-native, Tadawul-licensed; cleanest licensing path, depth unknown.*
- ✅ **Tadawul-licensed** local provider, 350+ companies (TASI + Nomu), REST + WebSocket, historical +
  dividends + events. Being exchange-licensed is a real R10 advantage.
- ❓ Delisted history and 2006 depth are **not documented** — the make-or-break unknowns for R1. A local
  licensed provider *may* hold the best survivorship data, or may only carry the live universe — trial decides.

**Twelve Data** — *convenient, adjusted; weak on the gating requirement.*
- ✅ Covers XSAU; split/dividend-adjusted. ❌ Delisted/survivorship not advertised; splits depth "last
  10+ years" hints shallow history. Best role: a **second source for R7 cross-vendor reconciliation**.

**Finnhub** — *real-time/recent focus; weakest for survivorship-free history.* Best role: reconciliation only.

**Saudi Exchange (official)** — *authoritative but shallow.*
- ❌ Official **EOD historical is only the past 5 years and listed instruments** → fails R1 outright for
  prices. ✅ But authoritative for the **calendar (R5)**, listing/delisting facts, and `eReference Data` —
  i.e. a prime input to the **human-curated PIT reference**, not a price backbone.

**Argaam / Mubasher** — *reference inputs, not a price API.* Deep Saudi fundamentals/news/filings →
valuable for curating delisting dates/reasons/terminal values and CA facts into the production reference;
not an OHLCV/survivorship price source.

## Ranking (evidence-weighted, for the survivorship-free CA-aware goal)

1. **LSEG Datastream (or Bloomberg/FactSet)** — highest probability of satisfying R1/R3/R4/PIT; the safe
   answer if budget allows. Friction: enterprise cost + license, overkill for price-only single-market.
2. **EODHD** — best affordable, mostly-confirmed on R2/R3 and 2006 depth; **gated solely on the Saudi
   delisted unknown (R1)**. If a trial confirms `.SR` delisted prices to 2006, this likely wins on cost.
3. **SAHMK** — Saudi-native + licensed (best R10 path); depth unknown. Strong candidate *and* the natural
   source/cross-check for the curated reference. Trial-decidable.
4. **Twelve Data** — second-source for R7 reconciliation; unlikely to pass R1 alone.
5. **Finnhub** — reconciliation only.
6. **Saudi Exchange + Argaam/Mubasher** — **reference-curation inputs** (calendar, delisting, CA), not the
   price backbone.

## Recommended architecture (no single source is confirmed)

Because R1 is unconfirmed for every affordable option, design for **composability**, decided by trial:

- **Prices + corporate actions (the OHLCV backbone):** EODHD **or** SAHMK — **whichever a trial proves on
  R1** (delisted Saudi prices to 2006). The vendor adapter (`../ingest/`) keeps this swappable.
- **Cross-vendor reconciliation (R7):** the other of EODHD/SAHMK, or Twelve Data — a second source to
  agree on adjusted closes across a corporate action.
- **PIT reference (curated, human — kept SEPARATE from vendor OHLCV):** delisting dates/reasons/terminal
  values, board/security-type intervals, and the exchange calendar, sourced from **Saudi Exchange
  announcements + Argaam/filings**, written into the production `reference/` tables. Never taken straight
  from a price feed (vendors are weak at PIT classification — this is the survivorship work).
- **Enterprise fallback:** if neither affordable trial passes R1, **LSEG/Bloomberg** is the way to
  *guarantee* survivorship-free Saudi history — accept the cost, or
- **Last resort:** manually reconstruct the *delisted set* from Tadawul announcements (the market is small,
  ~a few hundred securities ever) and source whatever delisted prices exist; a prices vendor covers the
  survivors. High curation effort; only if all vendor paths fail.

## What must be resolved by trial / direct confirmation (the open questions)

| # | Question | Vendor(s) | Resolves |
|---|---|---|---|
| Q1 | Are **delisted Saudi names** available with **daily prices back to ~2006**? | EODHD, SAHMK, (LSEG) | R1 — the decision |
| Q2 | Are **unadjusted + adjusted** both delivered (and is OHLC or only close adjusted)? | EODHD ✅close; SAHMK, TD | R2 |
| Q3 | Do **corporate actions** (splits/par/divs) reconcile the adjusted series? | EODHD, SAHMK | R3 |
| Q4 | Is there a **stable identifier** + ticker-change history (not the reusable 4-digit code)? | all | R4 |
| Q5 | Do **license terms** permit storing a **derived historical panel** for research? | all (esp. EODHD, LSEG) | R10 |
| Q6 | History **start date** and **gap/quality** for Saudi specifically? | EODHD, SAHMK | R1/R8 |

These map 1:1 onto the **trial-data request** in `WORKFLOW.md` and are answered objectively by the
**acceptance harness** (`acceptance/`) once a sample is in hand — turning "vendor claims" into pass/fail.

## Decision

**Do not select yet.** Request the trial sample (WORKFLOW.md §2) from **EODHD** and **SAHMK** in parallel,
run the acceptance harness on each, and confirm R10 license terms in writing. Select the cheapest source
that passes **every MUST on real sample data**; reach for LSEG/Bloomberg only if both affordable trials
fail R1.

## Sources

- EODHD: historical data API & academy (coverage from 2000-01-03 non-US; raw OHLC + adjusted_close;
  delisted-companies data US ~11k since 2000) — https://eodhd.com/financial-apis/api-for-historical-data-and-volumes ,
  https://eodhd.com/financial-apis/delisted-stock-companies-data ,
  https://eodhd.com/financial-academy/financial-faq/survivorship-bias-free-financial-analysis
- Twelve Data Saudi Exchange (XSAU): https://twelvedata.com/exchanges/XSAU , https://twelvedata.com/fundamentals
- Finnhub API/pricing: https://finnhub.io/docs/api , https://finnhub.io/pricing
- Saudi Exchange market data (EOD last 5 years; vendor licensing; eReference): https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/market-services/market-information-services/market-data
- SAHMK developers (Tadawul-licensed; 350+ TASI+Nomu; historical/dividends): https://www.sahmk.sa/en/developers
- Argaam: https://www.argaam.com/en  · Mubasher: https://english.mubasher.info/markets/TDWL/
- LSEG Datastream/Workspace (deep historical, delisted, 175 countries): https://www.lseg.com/en/data-analytics/financial-data/workspace-datasets
- ICE Tadawul catalog: https://developer.ice.com/fixed-income-data-services/catalog/saudi-stock-exchange-tadawul
