# Point-in-Time Reference Model — `research/reference/`

The **authoritative, hand-curated, version-controlled** source of *who was investable, and how they
were classified, on every historical date*. This — not the price vendor — is where survivorship
correctness lives. It is small enough to curate by hand precisely because TADAWUL is small (~300
securities ever), and that is the deliberate trade-off: manual upkeep in exchange for the highest
fidelity available and zero dependence on a vendor's (usually weak) point-in-time classification.

## What it answers

Given any date `D`, reconstruct the eligible universe exactly as it would have been known then:

```
eligible(D) = { sec_id :
      list_date(sec_id)  <= D
  AND (delist_date is null OR delist_date > D)
  AND board(sec_id, D)         == "main"          # authoritative (NOT the 9xxx heuristic)
  AND security_type(sec_id, D) == "stock"         # excludes reit/etf/fund/sukuk as-of D
  AND age_years(sec_id, D)     >= min_years }
```

Because classification is read from dated intervals, anachronism is impossible: a name has a
`board="nomu"` interval only from when Nomu existed (~2017), a `security_type="reit"` interval only
from when it was a REIT (~2016+). The eligibility *rules* are therefore implicitly time-aware.

## Tables (schemas in `schema/`, illustrative rows in `seed/`)

| Table | Grain | Purpose |
|---|---|---|
| `security_master` | one row / `sec_id` | identity, listing/delisting + reason + **terminal value**, lineage |
| `attribute_intervals` | interval / `(sec_id, attribute)` | time-varying `board` and `security_type` |
| `corporate_actions` | event / `(sec_id, ca_type, ex_date)` | splits / par changes / dividends for adjustment |
| `ticker_map` | interval / `(sec_id, valid_from)` | TADAWUL code ⇄ `sec_id`, with validity ranges |
| `exchange_calendar` | one row / date | trading days (captures the 2013 weekend change, Eid holidays) |

> The `seed/` CSVs are **illustrative scaffolding** (`source=illustrative`), present to exercise the
> schemas and the as-of logic. They are **not** vetted data and must be replaced by curated, sourced
> rows before any backtest is trusted.

## Stable security identifiers (`sec_id`) — the identity contract

**Decision.** Every security carries an opaque, immutable surrogate `sec_id` of the form `TDWL` + 6
zero-padded digits (e.g. `TDWL000002`). **All joins — panel, ledger, oracle, backtest — key on
`sec_id`, never on the ticker.**

**Why not the TADAWUL 4-digit code.** Exchange codes are *not* stable identifiers: they can be
reassigned after a delisting, and a company can change code/name. Keying on the ticker silently
merges two different companies that shared a code across time, or splits one company that changed
code — both are correctness bugs. The `ticker_map` resolves `(ticker, date) → at most one sec_id`.

**Allocation & immutability rules:**
1. Assigned **once**, monotonically, when a security first enters the master. **Never reused**, even
   after delisting. (Opaque/monotonic, not semantic — the number carries no meaning to depend on.)
2. **One `sec_id` = one continuously-identifiable listed instrument.** A rename or ticker change keeps
   the `sec_id` (add a `ticker_map`/attribute row). A Nomu→Main migration keeps the `sec_id` (a `board`
   interval change).
3. **Corporate lineage is explicit, not implied.** A merger/spin-off that creates a *new* listing gets
   a *new* `sec_id` with `succeeds_sec_id` pointing to its predecessor — so a backtest can both treat
   them as distinct instruments and follow the lineage when needed.

## Corporate-action adjustment policy (pinned)

- **Price-return series** (matches the screen's `Perf.*`): adjust for splits / reverse-splits / par
  changes / capital actions that change share count or par — **not** ordinary cash dividends.
- **Total-return series** (P&L only): additionally reinvest cash + special dividends at ex-date.
- The panel stores **both** `close` (adjusted, price-return) and `unadj_close` + `adj_factor` for audit;
  the two return bases are never blended (see `../spec/features.yaml` → `conventions.return_basis`).

## Curation & validation

- The reference is **git-tracked**; every change is a reviewable diff with a `source` and a
  `last_reviewed` date. The git history *is* the versioning.
- Integrity checks (CI): PK uniqueness; `sec_id` format; FK existence (`attribute_intervals`,
  `corporate_actions`, `ticker_map` → `security_master`); **no overlapping intervals** per
  `(sec_id, attribute)` and per `(sec_id)` in `ticker_map`; `delist_reason`/`terminal_value` present
  whenever `delist_date` is set; enums within range; `valid_from < valid_to` when `valid_to` is set.
- Build-time **historical reconciliation** (see `../validation/CONFORMANCE.md`) cross-checks the
  curated universe and corporate actions against a second source on known event dates.
