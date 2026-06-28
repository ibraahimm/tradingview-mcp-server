# Reference Curation — human-filled inputs to the production reference

Small, hand-curated facts that no price feed provides. These feed the production `reference/`
tables (and must pass `reference/validate.py --require-production`).

## `delisted_terminal_values.csv` — delisting terminal values (track #2)

The 20 delisted/suspended names found in the Saudi Exchange extract (price history present but
ending well before today). Their price series **stops** at delisting — but a backtest needs what
holders actually **received**, because a merger at a premium and a liquidation at ~0 look identical
in "price-then-stop" data. Curate one row each:

| Column | Fill with |
|---|---|
| `delist_reason` | `merged` / `acquired` / `suspended` / `liquidated` / `voluntary` / `regulatory` / `other` |
| `terminal_value` | the **SAR per share** holders realized (see method below) |
| `terminal_value_basis` | `cash` / `acquirer_stock` / `residual` / `zero` / `unknown` |
| `source` | where you confirmed it (Tadawul announcement, Argaam, filing) |
| `last_reviewed` | date you verified it |
| `notes` | exchange ratio / offer price / any caveat |

**Method by reason:**
- **Cash merger / acquisition** → cash paid per share = `terminal_value` (basis `cash`).
- **Share swap merger** → `exchange_ratio × acquirer_price_at_completion` (basis `acquirer_stock`;
  put the ratio + acquirer + date in `notes`). E.g. Alawwal `1040`→SABB, Samba `1090`→SNB,
  Sahara `2260`→Sipchem.
- **Liquidation / bankruptcy** → final distribution per share, often ≈ 0 (basis `residual`/`zero`).
- **Suspended then delisted with no consideration** → residual/last fair value, basis `residual`.

`sec_id`, `name`, `list_date`, `last_trade_date`, `n_bars` are pre-filled. The `last_trade_date` is
the delisting date to look up. Once filled, this populates `security_master.delist_reason` /
`terminal_value` / `terminal_value_basis`, which the event-study uses to label the final
forward return for each delisted name correctly.
