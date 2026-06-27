# Historical Data-Source Requirements

**Purpose.** Evaluate candidate data vendors by **explicit guarantees and acceptance tests**, not by
API convenience or marketing claims. Each requirement states *what breaks without it* and *how to
prove it* on a trial sample before any commitment. A vendor that cannot demonstrate a **MUST** on real
sample data is **rejected**, regardless of price, docs, or coverage claims.

**How to read this.** Tiers: **MUST** (a failure disqualifies), **SHOULD** (strongly weighted; absence
must be justified and back-filled by our own curation), **NICE** (credit if present). "Maps to" links
the requirement to the platform component it feeds (`../spec`, `../reference`, `../validation`,
`../ARCHITECTURE.md`). Run every **Acceptance test** against vendor-provided *sample* data, not a demo UI.

**Scope reminder.** This is a single-market (TADAWUL), **price-derived** strategy. We need *prices,
corporate actions, identifiers, calendar, and delisted history* — **not** fundamentals, intraday, or
multi-market. Do not pay for, or weight, capabilities the strategy does not use.

---

## The boundary we will not cross: illustrative vs production

Vendor data populates the **production** reference + panel directories **only**. It is never written to
`../reference/seed/` (illustrative scaffolding). Production reference rows must carry a real `source`
(never `illustrative`) and a `last_reviewed` date, and must pass:

```
python research/reference/validate.py --data <prod_dir> --require-production
```

If a vendor's export cannot be turned into rows that pass that gate, it is not production-ready.

---

## Requirements

### R1 — Survivorship-free universe, delisted coverage back through 2006  **(MUST)**
**Guarantee:** full daily history for securities that are **no longer listed** — merged, acquired,
suspended, liquidated — with coverage spanning at least the **2006 TASI cycle** onward.
**What breaks without it:** every backtest is survivorship-biased; failed/merged/suspended names vanish,
and the `DDmax`/`belowATH` depth anchoring (dominated by the 2006 bubble) is computed off a censored
universe. This is the single most important requirement.
**Acceptance test:** (a) request the *as-of* universe for **2008-01-01** and confirm it contains names
**not** listed today; (b) retrieve full history for a known delisted name (e.g. a 2019 merger casualty
such as Alawwal Bank / code 1040 — *verify independently*) and a 2006-era casualty; (c) count distinct
securities *ever* — it must materially exceed today's listed count.
**Maps to:** `reference/security_master` (delisting), survivorship; `ARCHITECTURE.md` §L2/§5.

### R2 — Adjusted **and** unadjusted OHLCV  **(MUST)**
**Guarantee:** both the **split/dividend-adjusted** series *and* the **raw unadjusted** series (or raw +
explicit adjustment factors), daily, with open/high/low/close/volume.
**What breaks without it:** we cannot reproduce or audit adjustments; `Perf.*`/EMA become unverifiable;
`52w high/low` and `ATH` need true high/low (close-only is a documented but avoidable delta).
**Acceptance test:** across a known split ex-date, the **adjusted close is continuous** while the
**unadjusted close jumps** by the split ratio; both series are retrievable for the same name/date range;
adjusted = unadjusted × reconstructable factor.
**Maps to:** panel `close`/`unadj_close`/`adj_factor`; `spec` price_basis; `reference/corporate_actions`.

### R3 — Corporate actions: splits, reverse splits, par/capital changes, dividends  **(MUST)**
**Guarantee:** an itemized corporate-action history with **ex-dates** and **ratios/amounts**, covering
splits, reverse splits, par-value changes, capital increases/decreases, bonus shares, and cash/special
dividends.
**What breaks without it:** we can neither verify the vendor's adjustment nor build our own
price-return-vs-total-return split; an undetected unadjusted split becomes a fake −80% "signal."
**Acceptance test:** for a name with a known split, the CA list contains it with correct ex-date + ratio;
the **factor reconstructed from the CA list reproduces the vendor's adjusted series** within tolerance.
**Maps to:** `reference/corporate_actions`; `spec` return_basis (price vs total).

### R4 — Identifier continuity (stable security ID, independent of the TADAWUL code)  **(MUST)**
**Guarantee:** a **stable per-security identifier** that survives ticker/name changes and is **not**
the reusable 4-digit exchange code, plus the **ticker-change history** to map code⇄ID over time.
**What breaks without it:** keying on the exchange code silently merges two different companies that
shared a reused code, or splits one company that changed code — corrupting every time series. This is
what our `sec_id` + `ticker_map` model exists to protect.
**Acceptance test:** a name that changed code/name retains **one** vendor ID across the change; a reused
code resolves to **distinct** IDs by date; the vendor can deliver the code↔ID validity ranges.
**Maps to:** `reference/security_master.sec_id`, `reference/ticker_map`; identity contract in
`reference/README.md`.

### R5 — Trading-calendar coverage  **(MUST for inference; SHOULD for explicit calendar)**
**Guarantee:** either an explicit TADAWUL **holiday/session calendar**, or bar dates clean enough to
**infer** trading days unambiguously — capturing the **2013 weekend change** (Thu–Fri → Fri–Sat) and Eid
closures.
**What breaks without it:** rolling 52-week and `Perf.*` windows misalign; naive calendar-day arithmetic
silently shifts every window.
**Acceptance test:** **no bars on known holidays**; the weekend pattern shift is visible across 2013;
inferred trading days reconcile with a published TADAWUL holiday list for a sample year.
**Maps to:** `reference/exchange_calendar`; `spec` calendar convention; `ARCHITECTURE.md` §5.

### R6 — Delisting metadata (date, reason, terminal value)  **(SHOULD, ideally MUST)**
**Guarantee:** for delisted names, the **delisting date**, **reason**, and ideally the **terminal value**
/ final consideration (cash or acquirer-stock exchange ratio).
**What breaks without it:** survivorship-free data still misstates returns if a bankruptcy delist is
marked at last-traded-price instead of recovery value. If the vendor lacks terminal value, we curate it
manually — hence SHOULD not MUST — but reason + date are near-mandatory.
**Acceptance test:** for the merger example, the vendor states reason = merged/acquired and (ideally) the
terminal value / exchange ratio.
**Maps to:** `reference/security_master.delist_reason/terminal_value`; backtest return labeling (§L5).

### R7 — Reconcilability against a second source / TradingView history  **(MUST)**
**Guarantee:** the data is **not a black box** — identifiable by ticker + date + currency so the same
series can be pulled from a **second vendor** or **TV history** and compared.
**What breaks without it:** we cannot run the historical reconciliation that validates the past (the
forward oracle is blind to 2006–2025); an unverifiable feed cannot be trusted as the substrate.
**Acceptance test:** pull the same name/date range from a second source (or TV history) and agree on
adjusted closes within the conformance tolerances for **N ≥ 30** dates spanning a corporate action.
**Maps to:** `validation/CONFORMANCE.md` (historical reconciliation, cross-vendor agreement).

### R8 — Coverage completeness & data quality  **(SHOULD)**
**Guarantee:** complete main-board coverage (Nomu optional), low gap rate, **suspended names flagged**
(not flat-filled), SAR-native prices, and **volume + value/turnover**.
**Acceptance test:** measured gap rate below an agreed threshold on a sample; a known suspended name is
flagged/empty over its suspension, not carried flat; turnover present for the liquidity (`value`) gate.
**Maps to:** L1 data-QA; `value` ADV/liquidity.

### R9 — Point-in-time classification (board / security type history)  **(NICE)**
**Guarantee:** historical board (main/nomu) and security-type (stock/reit/etf/fund/sukuk) **as-of**.
**Why only NICE:** we curate this ourselves in `reference/attribute_intervals` because most price vendors
lack it; credit a vendor that provides it (reduces curation), but its absence is not disqualifying.
**Maps to:** `reference/attribute_intervals`.

### R10 — Licensing & redistribution terms  **(MUST, legal)**
**Guarantee:** terms permit **research use**, storing a **derived historical panel**, and **bulk
historical retrieval** — no per-symbol/per-query model that blocks a full-history pull, no clause barring
derived storage.
**Acceptance test:** written confirmation that derived panels may be stored and used for internal
research, and that bulk history (not just latest) is in-scope.
**Maps to:** the entire panel build; reproducibility (§L8).

### R11 — Delivery, vintage & schema stability  **(SHOULD)**
**Guarantee:** **bulk** historical download (not just latest), a **stable schema**, and ideally
**point-in-time / vintage** semantics so a dump can be re-pulled or dated for reproducibility.
**Acceptance test:** a dated bulk export reproduces byte-for-byte (or row-for-row) on re-pull; schema
documented and versioned.
**Maps to:** L1 immutable vintage dumps; run-manifest provenance (§L8).

### R12 — Operational fit (rate limits, cost)  **(NICE / context)**
**Guarantee:** rate limits and pricing compatible with a **one-time full-history pull** plus periodic
refresh of a small market.
**Maps to:** ingestion ops.

---

## Hard disqualifiers (any one ⇒ reject)

- **No delisted history** / survivorship-only universe (fails R1).
- **No unadjusted series and no itemized corporate actions** — adjustment cannot be verified (R2+R3).
- **Black-box identifiers** that cannot be reconciled against a second source / TV (R4+R7).
- **License forbids storing a derived panel** or blocks bulk history (R10).
- **Coverage starts after the 2006 cycle** for old names — the depth-anchoring regime is missing (R1).

---

## Acceptance-test protocol (run before committing)

Request a **trial sample** sufficient to run the tests above — do not evaluate on a UI/marketing demo:

1. Full daily OHLCV (adjusted **and** unadjusted) for: one large-cap (e.g. 2222), one long-listed name
   spanning 2006, one **delisted** name (merger), one **suspended/liquidated** name.
2. The corporate-action history for those names.
3. The identifier/ticker-change record for a name that changed code or name.
4. The trading-calendar (or enough bar dates to infer it) across 2012–2014 (to see the weekend change).
5. The **as-of universe** for 2008-01-01 (to prove survivorship-free membership).

Then execute R1–R7 acceptance tests on that sample and record evidence in the scorecard. A vendor passes
the gate **only if every MUST passes on real sample data.**

---

## Scorecard

Use `scorecard_template.csv`. MUST rows are **pass/fail gates** (any fail ⇒ reject); SHOULD/NICE rows are
scored 0–3 and weighted. The final recommendation is: *all MUST pass* **and** highest weighted SHOULD/NICE
score, with evidence attached for every row. Marketing claims without sample-data evidence score 0.

---

## Mapping summary (requirement → platform component)

| Req | Feeds |
|---|---|
| R1, R6 | `reference/security_master`, survivorship, return labeling |
| R2, R3 | panel adjusted/unadjusted close, `reference/corporate_actions`, price/total-return split |
| R4 | `reference/security_master.sec_id`, `reference/ticker_map`, identity contract |
| R5 | `reference/exchange_calendar`, all window indexing |
| R7 | `validation/CONFORMANCE.md` historical reconciliation + cross-vendor |
| R8 | L1 data-QA, `value` liquidity gate |
| R9 | `reference/attribute_intervals` (else self-curated) |
| R10, R11, R12 | ingestion, vintage dumps, provenance |

*Vendor selection remains deferred until a candidate demonstrably passes every MUST on sample data.*
