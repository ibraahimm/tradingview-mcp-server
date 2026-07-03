
# HANDOFF — TradingView MCP + Saudi Wave Screening + Research Platform

**Updated:** 2026-07-03 · **Branch:** `feat/tasi-w1-screen` · **HEAD:** see `git log --oneline -14`
(this session: documentation architecture + decision log, the Tier-1 SSOT lint, the CI-YAML fix, and the
**canonical rename `W1/W2/W3 → TASI-W1/TASI-W2/TASI-W3`**). All work committed and pushed to `mine`.

> This file is a **map, not a substitute** for the repo. The repository is the source of truth. It is
> **Session state** (disposable, per [`/DOCUMENTATION.md`](../DOCUMENTATION.md)) — it summarizes by
> reference and restates no canonical numbers. To continue in a new chat, use `.claude/SESSION_START.md`,
> which points here plus at `/DOCUMENTATION.md`, `research/ARCHITECTURE.md`, `research/spec/TESTING.md`,
> `research/spec/rules.yaml`, `research/spec/decisions.md`, `.claude/commands/saudi-*.md`, and `git log`.

---

## 1. What this repo is (three subsystems)

1. **TS MCP server + CLI** (`src/`) — the TradingView screener wrapper (unchanged core).
2. **Saudi wave screening — the live product** (`.claude/commands/` + `.claude/scripts/`) — on-demand
   slash commands `/tasi-w1` (TASI-W1), `/tasi-w2` (TASI-W2), `/tasi-w3` (TASI-W3), `/tasi-track` (tracker),
   each = MCP screen → node helper → print. Persistent CSVs in `.claude/outputs/`.
3. **Research / backtesting platform** (`research/`, Python + polars) — answers, with rigor, whether the
   wave methodology has a real edge, and keeps the live screens honest.

## 2. The documented methodology (lifecycle)

`collapse → TASI-W1 (deep-correction first-wave ENTRY) → TASI-W2 (re-coil continuation of TASI-W1 names) → TASI-W3 (mature
re-coil in a normal trend)`. The **tracker** = one journey per symbol across waves.

**Current OFFICIAL gate values** — canonical in [`research/spec/rules.yaml`](../research/spec/rules.yaml)
(`TASI-W1`/`TASI-W2`/`TASI-W3` → `params`), mirrored in the live JS and parity-locked by `methodology_parity.py`; change
history in [`research/spec/decisions.md`](../research/spec/decisions.md). **Read the numbers from
`rules.yaml`; this Session doc does not restate them.**

- **TASI-W1** (`/tasi-w1`) — deep-correction first-wave entry: listing-age, `DDmax`, `belowATH`, `offLow`,
  and `Perf.3M/6M/3Y/5Y/10Y` gates. ext60 extension cap removed (`decisions.md` D-2026-06-30-01).
- **TASI-W2** (`/tasi-w2`) — re-coil continuation of TASI-W1 names: `close>EMA60`, the `EMA21/EMA60` coil, reclaim
  `close≥EMA21` (ext21 upper cap removed), plus the deep-correction DNA (`DDmax`/`belowATH`/`offLow`) and Perf gates.
- **TASI-W3** (`/tasi-w3`) — mature re-coil near highs: `close>EMA200`, coil, `nrHi` band, `Perf.3Y` minimum
  (the discriminator). Not changed this session.
- **Tracker** (`/tasi-track`): committed methodology is **TASI-W1/TASI-W2 only**. States `ACTIVE-TASI-W1/TASI-W2`, `GRAD★`,
  `FAILED`, `STALE`, `EXPIRED`; badges `NEW/PROMOTED/nearATH`; metric `gainSinceSignal`. Its lifecycle
  thresholds are owned by `.claude/scripts/tasi-track.js` (not `rules.yaml`). TASI-W3-in-tracker proposed
  earlier, never committed (see Open items).

## 3. Research platform (`research/`)

- **`spec/rules.yaml`** — canonical TASI-W1/TASI-W2/TASI-W3 rule definitions (funnels + params). **Single source of truth**;
  the live JS is kept in parity with it (parity gate).
- **`engine/`** — polars feature engine (`panel.py`) + `rules.py` (`evaluate_frame(rule, df, params_overrides)`).
- **`backtest/`** — `event_study`, `governance` (time-split / walk-forward / Bonferroni), `rigor` (dedup +
  market-neutral excess), `robust` (net-of-cost + block-bootstrap + `prob_greater`), `regime`, `lifecycle`,
  `tracker` (faithful port of `tasi-track.js`), `replay`. Each has a `selftest_*.py` CI gate.
- **`spec/conformance/`** — `reference_runner.py` (feature vectors), `rule_runner.py` (rule vectors),
  **`methodology_parity.py`** (live JS ↔ rules.yaml params **+ Tier-1 SSOT lint**: command-doc Step-2
  `(default N)` annotations ↔ rules.yaml).
- **CI:** `.github/workflows/research-ci.yml`.
- **`RIGOR_RESULT.md`** — the full findings write-up (a dated Report; point-in-time).

## 4. Governance & documentation architecture — READ THIS

- **Methodology change convention** (`research/spec/TESTING.md`): official methodology lives ONLY in
  `rules.yaml` + live JS + docs, parity-locked; experiments live in `research/experiments/` (runtime
  overrides only, never edit official files; outputs are hypotheses); promotion = edit canon + JS + docs +
  vectors together.
- **Documentation architecture** ([`/DOCUMENTATION.md`](../DOCUMENTATION.md), the governing model — decision
  D-2026-07-02-02): every doc-fact has one home (fact-type × lifetime; single-home §5 table; seam rule §6).
  The **decision log** [`research/spec/decisions.md`](../research/spec/decisions.md) is the append-only home
  of every methodology/governance decision. `spec_version` versions the **feature spec only**; rule
  threshold/structural changes are Methodology Decisions, **not** `VERSION` bumps (D-2026-07-02-01).
- **SSOT is CI-guarded:** `methodology_parity.py` now also enforces that command-doc Step-2 defaults match
  `rules.yaml` (Tier-1 lint, D-2026-07-02-03). LIMITATION: parity checks parameter values, not full
  behavioral equivalence.

## 5. Key findings (so you don't re-derive them)

- **`ext60_max` cap: statistically INERT** over 20 years → removed.
- **TASI-W1: no cross-sectional (selection) edge** — a **TIMING/beta** expression, crisis-concentrated. Good as a
  *recall* screen; most misses are *correct exclusions*.
- **TASI-W2: real SELECTION edge — but only in NORMAL regimes**, and it does **NOT** cleanly survive ~31 bps cost.
- **TASI-W3 @120d: the one candidate that survives the FULL gauntlet** (market-neutral, deflated, block-bootstrap,
  net-of-cost, ≈ +2.3% net). Still needs a **120-day walk-forward** + true OOS.
- **Lifecycle:** `TASI-W1→TASI-W2` is the tradeable refinement; **TASI-W3 marks completion (buy-late), not an entry.**
- **Forward-backtest of the adopted TASI-W1/TASI-W2 band-widening: RETURN-NEUTRAL** — no per-signal improvement vs the
  prior params across horizons. Retained as a *selective-entry* choice, **not** an edge claim
  (`decisions.md` D-2026-07-01-02).

## 6. Methodology change history

All OFFICIAL methodology changes are recorded, with rationale + validation status, in the **decision log**
[`research/spec/decisions.md`](../research/spec/decisions.md) — the single home of that fact. This session:
ext60 removal (D-2026-06-30-01), TASI-W1 `below_max` (D-2026-06-30-02), the formal TASI-W1/TASI-W2 `offLow`/`Perf` band
widening (D-2026-07-01-01), and the decision to **retain** it after forward testing found it return-neutral
(D-2026-07-01-02). **Deltas are not restated here** — read choice + validation status in the log; numbers by
reference to `rules.yaml`.

**Governance decisions this session** (same log): `spec_version` scoping — rule changes are Decisions, not
`VERSION` bumps (D-2026-07-02-01); adoption of the **documentation architecture** `DOCUMENTATION.md`
(D-2026-07-02-02); the **Tier-1 SSOT lint** in `methodology_parity.py` (D-2026-07-02-03); the CI-outage
record + workflow fix (D-2026-07-02-04); and the **canonical rename `W1/W2/W3 → TASI-W1/TASI-W2/TASI-W3`**
(D-2026-07-02-05) — behavior-preserving, no `VERSION` bump, all gates green, live ledger migrated. Its
execution report is [`research/reports/canonical-rename-2026-07-02.md`](../research/reports/canonical-rename-2026-07-02.md);
the ledger rollback backup is `.claude/outputs/saudi-tracker.jsonl.bak-2026-07-02`.

## 7. Data

- **`research/panel/tadawul_2026-06-28.parquet`** — the working panel. **GITIGNORED, never committed**
  (Saudi Exchange licensed + large). Vintage 2026-06-28: 951,419 rows / 291 securities / 2001-12-31→2026-06-25,
  fingerprint `60cbf970…`. Manifest **is** committed: `research/ingest/manifests/tadawul_2026-06-28.json`.
- Regenerate via `research/ingest/ingest_tadawul.py` from the raw extract (`ingest/raw/`, gitignored).
  Survivorship-inclusive (20 delisted with curated terminals in `research/reference/curation/`).

## 8. Git / push setup

- Remote **`mine` = `git@github.com:ibraahimm/tradingview-mcp-server.git` (SSH)**; deploy key
  `~/.ssh/mine_tadawul` + repo `core.sshCommand` configured → `git push mine feat/tasi-w1-screen` works here.
- `origin` = `fiale-plus` fork (HTTPS, not for push). **Never commit `package-lock.json`.**
  `.claude/` is gitignored → `git add -f` for new files (already-tracked ones add normally).
- **Canon (`features.yaml`, `rules.yaml`, `VERSION`) changes only with separate explicit approval**, and get
  their own commit even when cosmetic.

## 9. Open items / next steps

1. **TASI-W3 @120d walk-forward** (confirm it holds pre-2020, not just recency) + true OOS on a future vintage.
2. (Optional) **Boundary golden vectors** for the current thresholds (e.g. `offLow` / `Perf.6M` edges) under CI.
3. (Optional) **TASI-W3-in-tracker** integration (source=TASI-W3, ACTIVE-TASI-W3) — proposed earlier, never committed.
4. (Deferred, needs own review) **Command Step-2 → read defaults from `rules.yaml` at run time** — removes the
   last runtime canon duplication; a live-product behavioral change (currently guarded, not eliminated).
5. (Deferred, not rejected) **Tier-2 SSOT lint** (general canon-number-outside-canon scanner + marker
   allowlist) — revisit only if reference-only doc drift recurs.
6. (Low priority, CI hygiene) Bump `actions/checkout` / `setup-python` / `setup-node` to versions that
   natively run on Node 24 — CI currently warns it is forcing Node 24 on the v4/v5 pins. Non-blocking;
   do before Node 20 is fully removed. (CI enforcement itself is restored — `decisions.md` D-2026-07-02-04.)

**Working-tree note (intentional — do not "clean up"):** two items are deliberately uncommitted — a modified
`package-lock.json` (not ours; never commit) and the untracked experiment
`research/experiments/w1w2_param_forward_backtest.py` (kept local per an earlier call; the return-neutral
finding it produced is recorded in D-2026-07-01-02). A fresh `git status` shows both; leave them.

## 10. How to run

- **Live screens:** `/tasi-w1`, `/tasi-w2`, `/tasi-w3`, `/tasi-track`.
- **Conformance/parity:** `python research/spec/conformance/{rule_runner,methodology_parity,reference_runner}.py`,
  `python -m research.engine.selftest_screen`, `python -m research.backtest.selftest_{tracker,replay,rigor,robust,regime,lifecycle}`.
- **Backtests:** `python -m research.{rigor_run,robust_run,regime_run,lifecycle_run,replay_run} research/panel/tadawul_2026-06-28.parquet`.
- **Experiments (hypotheses only):** `python -m research.experiments.{w1_replay_60d,w1_variant_replay,w1_p6m_variants,w1w2_param_forward_backtest,wave_start_study} research/panel/tadawul_2026-06-28.parquet`.
