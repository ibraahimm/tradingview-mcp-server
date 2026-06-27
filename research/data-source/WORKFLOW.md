# Data-Layer Phase — Workflow

Gets us from the synthetic-tested platform to the **first real, out-of-sample evaluation** on
historical Tadawul data. Driven by `REQUIREMENTS.md`; nothing here weakens those MUST gates.

## The path (and where the gates are)

```
[1] Vendor shortlist        -> candidates that *claim* the MUST capabilities
[2] Trial-data request      -> a fixed, minimal sample (below) from each candidate
[3] Acceptance harness       -> automate the MUSTs that can be automated (acceptance/)   <- CI-gated
[4] Human review             -> the partial/qualitative MUSTs (cross-vendor, calendar truth)
[5] Decision (scorecard)     -> all MUST pass on REAL sample data, else reject
[6] Ingestion                -> normalize the chosen vendor -> canonical OHLCV frame (ingest/)
[7] PIT reference curation   -> human-built production reference (SEPARATE from vendor OHLCV)
[8] First panel + screen     -> build_panel -> screen run -> event study -> governance
```

No vendor is selected, and no production data is ingested, until **[5]** — a candidate that passes
every MUST **on sample data**, not on marketing claims.

## [2] Trial-data request (what to ask every candidate for)

A small, fixed sample sufficient to run the harness — **not** a UI demo:

| Item | Why (which MUST it exercises) |
|---|---|
| Daily OHLCV (adjusted **and** unadjusted + `adj_factor`) for **4 names**: a large-cap, a name **listed before 2006**, a **delisted-by-merger** name, a **suspended/liquidated** name | R1 survivorship, R2 adjust, R5 calendar |
| Corporate-action history (splits/par/dividends with ex-date + ratio/amount) for those names | R3, R2 |
| Identifier/ticker-change record for a name that **changed code or name** | R4 |
| The **as-of universe for 2008-01-01** (proves delisted names were members then) | R1 |
| Delisting metadata (date + reason + terminal/exchange value) for the delisted names | R6 |

Delivered as the tables in `acceptance/README.md` (or normalized to them). One name **must** have a
split, and one **must** be delisted before today and listed pre-2006 — otherwise the MUSTs can't be
verified and the sample is incomplete.

## [3]/[4] Automatable vs human

| Requirement | Automatable (acceptance harness) | Human |
|---|---|---|
| R1 survivorship / delisted / 2006 span | ✅ fully | spot-check the delisting facts |
| R2 adjusted **and** unadjusted | ✅ split-continuity check | — |
| R3 corporate actions reconcile adjustment | ✅ reconstruct `adj_factor` from CAs | — |
| R4 identifier continuity | ✅ stable surrogate + no concurrent ticker reuse | — |
| R6 delisting metadata present | ✅ | verify terminal values are correct |
| R5 trading calendar | ⚠️ partial (dup/monotonic) | **holiday-calendar truth, 2013 weekend change** |
| R7 reconcilable vs 2nd source / TV | ⚠️ partial (structural joinability) | **the actual cross-vendor/TV reconciliation (needs a 2nd sample)** |
| R10 license | ❌ | **legal review of terms** |

So the harness gives an objective first cut; a human closes R5/R7/R10 before any commitment.

## [6] Ingestion (shape the engine needs)

The chosen vendor's export is **normalized** to the canonical OHLCV frame in `../ingest/` — the exact
input `engine/panel.build_panel` already consumes (`sec_id, date, open, high, low, close [adjusted],
unadj_close, adj_factor, volume`). Normalization + the L1 data-QA gate are the **next** data-layer
increment; the schema is defined now so that work has a fixed target.

## [7] Production reference is SEPARATE from vendor OHLCV

Critical separation (see `../reference/README.md`):

- **Vendor delivers**: adjusted/unadjusted **prices** + **raw corporate actions** + raw listing/
  delisting facts. These are *inputs*.
- **We curate (human)**: the **point-in-time universe** — `sec_id` identity, board/security-type
  intervals, delisting reasons + terminal values, the exchange calendar. This is the production
  `reference/` data, hand-built and version-controlled, and it **never** comes straight from a vendor
  feed (vendors are weak at PIT classification; this is the survivorship work).

The vendor's listing/delisting/CA data *informs* curation, but the authoritative production reference
table is written by a human and must pass `reference/validate.py --require-production`.

## Definition of done for this phase

A chosen vendor passes every MUST on sample data; its history is normalized to the canonical OHLCV
frame and QA-clean; the production reference table is curated and passes the production gate; and
`build_panel → screen → event_study → governance` runs on **real** data to produce the first
out-of-sample `ext60_max` result.
