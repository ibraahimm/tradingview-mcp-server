# Vendor Acceptance Harness — `research/data-source/acceptance/`

Turns the **MUST** requirements (`../REQUIREMENTS.md`) into **automated pass/fail** over a vendor
TRIAL sample, so vendor *claims* become *evidence* (see `../WORKFLOW.md`, `../VENDOR_EVALUATION.md`).
Stdlib only — no dependencies.

```
python research/data-source/acceptance/run_acceptance.py <sample_dir>   # scorecard; exit!=0 if a MUST fails
python research/data-source/acceptance/selftest_acceptance.py            # CI gate (good passes / bad fail)
```

## Sample contract (what a candidate's trial sample is normalized to)

Four CSVs in `<sample_dir>/` (omit a file ⇒ treated as empty):

| File | Columns |
|---|---|
| `securities.csv` | `vendor_id, ticker, name, list_date, delist_date, delist_reason, terminal_value` |
| `prices.csv` | `vendor_id, date, open, high, low, close, close_unadj, adj_factor, volume` |
| `corporate_actions.csv` | `vendor_id, ca_type, ex_date, ratio, amount` |
| `ticker_history.csv` | `vendor_id, ticker, valid_from, valid_to` |

**Adjustment contract:** `close = close_unadj * adj_factor` (adjusted = unadjusted × an accumulating
split factor). `vendor_id` is the vendor's stable security id; `ticker` is the (reusable) exchange code.

## What each check verifies

| Req | Tier | Automated check |
|---|---|---|
| **R1** | MUST | delisted names present **and** earliest price ≤ 2006-12-31 **and** some names not listed today |
| **R2** | MUST | `close`/`close_unadj`/`adj_factor` present; across a split, unadjusted jumps by the ratio while adjusted close is continuous |
| **R3** | MUST | corporate actions present; `adj_factor` reconstructed from splits matches the vendor's, and `close == close_unadj·adj_factor` |
| **R4** | MUST | `vendor_id` is a stable surrogate (≠ ticker), a ticker change keeps the same `vendor_id`, no code maps to two ids concurrently |
| **R6** | MUST | every delisted security has a `delist_reason` and `terminal_value` |
| **R5** | PARTIAL | no duplicate `(vendor_id, date)`; holiday-calendar truth + the 2013 weekend change are a **human** follow-up |
| **R7** | PARTIAL | structurally reconcilable (ticker+date keys); the actual cross-vendor / TradingView reconciliation needs a **second sample** + a human |

R10 (license to store a derived panel) is **not** automatable — it is a written-terms review (see WORKFLOW).

## Fixtures (and the self-test gate)

- `samples/good/` — passes every MUST (a delisted pre-2006 name, a split that reconciles, a ticker change).
- `samples/bad_survivorship/` — only live names, post-2006 ⇒ **fails R1** (and R6).
- `samples/bad_unadjusted/` — prices without `close_unadj`/`adj_factor`, no corporate actions ⇒ **fails R2 + R3**
  while still passing R1/R4/R6 (isolates the adjustment failure).

`selftest_acceptance.py` asserts exactly these outcomes — proving the harness *discriminates* rather than
vacuously passing. It is wired into CI.

## Using it on a real trial

Normalize each candidate's trial export (EODHD, SAHMK, …) into the four CSVs above, run
`run_acceptance.py`, and record the scorecard in `../scorecard_template.csv`. Select the cheapest
vendor that passes **every MUST on real sample data**; close R5/R7/R10 by human review.
