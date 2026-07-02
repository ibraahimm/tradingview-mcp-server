# Canonical Rename — Execution Report (2026-07-02)

> **Point-in-time Report** — dated, not maintained (per [`/DOCUMENTATION.md`](../../DOCUMENTATION.md) §4).
> The **authoritative decision** is `research/spec/decisions.md` **D-2026-07-02-05**; this Report is its
> evidence per the seam rule (§6). Commit: `a1915b0`.

## Outcome
`W1/W2/W3` → **`TASI-W1/TASI-W2/TASI-W3`** as the canonical identifiers. **Behavior-preserving**, executed
as a **single atomic commit** (55 files); all gates green on the committed tree. No methodology change;
`spec_version` stays `1.0.0` (no `VERSION` bump).

## Renamed (the canonical surface)
- **Canon:** `rules.yaml` keys (keys only — scoped approval).
- **Consumers:** engine/backtest/parity string keys, `*_run.py`, 4 experiments.
- **Conformance:** `rule_vectors/*/case.json` rule field; `lifecycle_vectors` **regenerated** from the
  renamed generator + the live JS (`stage=conform`).
- **Live tracker:** source tags, states `ACTIVE-TASI-W1`, journeys `TASI-W1→TASI-W2`.
- **Docs:** ARCHITECTURE, HANDOFF, SESSION_START, DOCUMENTATION, TESTING, READMEs, command docs, index.

## Proofs
| Check | Result |
|---|---|
| Full gate suite on the committed tree | **17/17 PASS** (incl. `rule_runner`, `methodology_parity`, `selftest_tracker` Py==golden==live JS) |
| Ledger migration | **200 tags** (`source` + `first_source`); run #2 = **0** (idempotent) |
| Journey continuity | **37 symbols identical** — journeys/states relabeled, none broken (`ACTIVE-W1 28` → `ACTIVE-TASI-W1 28`) |
| Experiment smoke-run vs panel | **exit 0** — `rules["TASI-W1"]` resolves end-to-end |

## Bug caught + fixed (non-gated)
The mechanical rename also hit Python **variable identifiers** (`W1 = …` → invalid `TASI-W1 =`). CI stayed
green because gated code uses only the *string* `"TASI-W1"`; 4 non-gated experiments would not compile.
Fixed the **code identifiers** to `TASI_W1` while keeping string keys `"TASI-W1"`; verified by recompiling
all research Python + the smoke-run.

## Preserved (point-in-time, unchanged)
`RIGOR_RESULT.md` body and all prior decision entries keep `W1/W2/W3`. The Report carries a provenance-only
editorial annotation legalized by an explicit clause in D-2026-07-02-05.

## Rollback
`git revert a1915b0`; restore the live ledger from `.claude/outputs/saudi-tracker.jsonl.bak-2026-07-02`.

## Follow-up (separate, after this report)
The one stale `rules.yaml` comment (`… (W2 inverts W1)`) is aligned to the TASI names in a standalone
comments-only commit (see `git log`).
