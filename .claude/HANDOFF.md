# HANDOFF — TradingView MCP + Saudi Wave Screening + Research Platform

**Updated:** 2026-07-01 · **Branch:** `feat/saudi-stage2-screen` · **HEAD:** `e7bd6ef` (pushed to `mine`)

> This file is a **map, not a substitute** for the repo. The repository is the source of truth.
> To continue in a new chat, provide this file **plus** point the assistant at:
> `research/ARCHITECTURE.md`, `research/spec/TESTING.md`, `research/spec/rules.yaml`,
> `.claude/commands/saudi-*.md`, and `git log`.

---

## 1. What this repo is (three subsystems)

1. **TS MCP server + CLI** (`src/`) — the TradingView screener wrapper (unchanged core).
2. **Saudi wave screening — the live product** (`.claude/commands/` + `.claude/scripts/`) — on-demand
   slash commands `/saudi-stage2` (W1), `/saudi-wave2` (W2), `/saudi-wave3` (W3), `/saudi-track` (tracker),
   each = MCP screen → node helper → print. Persistent CSVs in `.claude/outputs/`.
3. **Research / backtesting platform** (`research/`, Python + polars) — built this session to answer, with
   rigor, whether the wave methodology has a real edge, and to keep the live screens honest.

## 2. The documented methodology (lifecycle)

`collapse → W1 (deep-correction first-wave ENTRY) → W2 (re-coil continuation of W1 names) → W3 (mature
re-coil in a normal trend)`. The **tracker** = one journey per symbol across waves.

**Current OFFICIAL gate values** (after this session's changes — authoritative in `research/spec/rules.yaml`,
mirrored in the live JS, parity-locked):

- **W1** (`/saudi-stage2`): `min_years≥5`, `DDmax≥50`, `belowATH∈[40,100]`, `offLow∈[35,80)`,
  `Perf.3M∈[5,40)`, `Perf.6M∈(-30,50)`, `Perf.3Y<100`, `Perf.5Y<100`, `Perf.10Y<250`. **ext60 cap REMOVED.**
- **W2** (`/saudi-wave2`): the re-coil of W1 names — `close>EMA60`, coil `EMA21/EMA60∈[-2,5]`, **reclaim**
  `close≥EMA21` (ext21 upper cap REMOVED), `offLow∈[35,80)`, `Perf.1M∈(0,15)`, `Perf.6M∈(-10,80)`,
  `Perf.1Y>0`, `Perf.3Y<130`, `belowATH∈[20,80]`, `DDmax≥45`.
- **W3** (`/saudi-wave3`): mature re-coil near highs, `close>EMA200`, coil, `nrHi∈[78,98]`, `Perf.3Y≥50`
  (the discriminator). *Not* changed this session.
- **Tracker** (`/saudi-track`): committed methodology is **W1/W2 only**. States `ACTIVE-W1/W2`, `GRAD★`
  (`Perf.5Y>2000`), `FAILED` (`close<first_close AND vs200<0`), `STALE` (>120d), `EXPIRED` (>1826d);
  badges `NEW/PROMOTED/nearATH`; metric `gainSinceSignal`. W3-in-tracker was proposed earlier but never
  committed (see Open items).

## 3. Research platform (`research/`)

- **`spec/rules.yaml`** — canonical W1/W2/W3 rule definitions (funnels + params). **Single source of truth**;
  the live JS is kept in parity with it (see the parity gate).
- **`engine/`** — polars feature engine (`panel.py`: EMA/perf/DDmax/belowATH/offLow/nrHi/age/value…) +
  `rules.py` (the funnel evaluator: `evaluate_frame(rule, df, params_overrides)`).
- **`backtest/`** — `event_study` (forward returns + delisting terminal values), `governance` (time-split /
  walk-forward / Bonferroni deflation), `rigor` (non-overlap dedup + market-neutral excess), `robust`
  (net-of-cost + block-bootstrap `prob_greater`), `regime` (PIT market-regime), `lifecycle` (W1→W2→W3
  linkage + prob_greater), `tracker` (faithful Python port of `saudi-tracker.js`), `replay` (historical
  event generation from the panel). Each has a `selftest_*.py` CI gate.
- **`spec/conformance/`** — `reference_runner.py` (spec golden vectors), `rule_runner.py` (rule vectors),
  **`methodology_parity.py`** (live JS ↔ rules.yaml param parity).
- **CI:** `.github/workflows/research-ci.yml` (foundation gates + engine-conformance; node available so the
  tracker JS↔Python differential runs).
- **`RIGOR_RESULT.md`** — the full findings write-up.

## 4. Governance conventions (`research/spec/TESTING.md`) — READ THIS

- **Official methodology** lives ONLY in `rules.yaml` + the live JS + docs, and is **parity-locked**.
- **Conformance/parity** = CI gates asserting internal consistency and JS≡spec at default params.
- **Experiments** = `research/experiments/` — **runtime overrides only, never edit official files**; each
  file carries an `EXPERIMENTAL` banner; outputs are **hypotheses**, not methodology.
- **Promotion path** (experiment → official): edit `rules.yaml` + the JS + docs (+ golden vector), which the
  parity gate then forces to stay consistent. `methodology_parity.py` LIMITATION: checks **parameter
  parity, not full behavioral equivalence** (a logic/operator change with no param change wouldn't be caught).

## 5. Key findings this session (so you don't re-derive them)

- **`ext60_max` cap: statistically INERT** over 20 years → removed.
- **W1: no cross-sectional (selection) edge** — it's a **TIMING/beta** expression, crisis-concentrated
  (esp. 2008). As a *recall* screen it catches most structurally-eligible recovery names; its misses are
  mostly *correct exclusions* (shallow corrections, mature 3-year winners, recent IPOs) plus a small
  "too recent" bucket (`Perf.6M≤0`).
- **W2: real SELECTION edge — but only in NORMAL regimes**, and it does **NOT** survive ~31 bps round-trip cost.
- **W3 @120d: the one candidate that survives the FULL gauntlet** (market-neutral, deflated, cluster-robust
  block bootstrap, AND net-of-cost, ≈ +2.3% net). Still needs a **120-day walk-forward** + true OOS.
- **Lifecycle:** `W1→W2` is the tradeable refinement; **W3 marks completion (buy-late), not an entry.**
- **Variant experiments:** a *later* `offLow` entry is **strictly worse for recall**; relaxing `p6m_min`
  raises recall but the added names are **mostly low quality** (dead-cat) on the 60-day proxy.

## 6. Methodology changes made OFFICIAL this session

- ext60 extension cap **removed** (W1 & W2). W1 `below_max` **95→100**. Formal user request (2026-07-01):
  W1 `offLow[20,60)→[35,80)`, `Perf.6M(0,50)→(-30,50)`, `Perf.3Y<50→100`, `Perf.5Y<80→100`; W2
  `offLow[30,100)→[35,80)`, `Perf.6M(3,80)→(-10,80)`, `Perf.3Y<100→130`.
- **Caveat (important):** the formal W1/W2 change was validated only as **more selective on a 60-day recall
  snapshot** (W1 49→26, W2 19→14 detections) — it was **NOT forward-return backtested**. Adopted at the
  user's explicit, evidence-in-hand request as a selective-entry choice.
- Commits: `ae11d1d` (methodology), `e7bd6ef` (governance: parity gate + TESTING.md + experiments split).

## 7. Data

- **`research/panel/tadawul_2026-06-28.parquet`** — the working panel. **GITIGNORED, never committed**
  (Saudi Exchange licensed + large). Vintage 2026-06-28: **951,419 rows / 291 securities /
  2001-12-31→2026-06-25**, fingerprint `60cbf970…`. Manifest **is** committed:
  `research/ingest/manifests/tadawul_2026-06-28.json`.
- Regenerate via `research/ingest/ingest_tadawul.py` from the raw Saudi Exchange extract (`ingest/raw/`,
  also gitignored). Adjusted (split/bonus) series; survivorship-inclusive (20 delisted with curated
  terminal values in `research/reference/curation/delisted_terminal_values.csv`).

## 8. Git / push setup (SOLVED this session)

- Remote **`mine` = `git@github.com:ibraahimm/tradingview-mcp-server.git` (SSH)**. Deploy key
  `~/.ssh/mine_tadawul` + repo-level `core.sshCommand` are configured, so `git push mine
  feat/saudi-stage2-screen` **works from this environment**. (The old HTTPS URL couldn't auth here.)
- `origin` = `fiale-plus` fork (HTTPS, not used for push). **Never commit `package-lock.json`.**
  `.claude/` is gitignored → force-add specific files (`git add -f`).

## 9. Open items / next steps

1. **Forward-backtest the new W1/W2 params** (they were only recall-validated, not for forward returns) —
   run through the rigor/robust framework on the vintage panel before trusting them as an edge.
2. **W3 @120d walk-forward** (confirm it holds pre-2020, not just recency-driven) + true OOS on a future vintage.
3. (Optional) Add **boundary golden vectors** for the new thresholds (`offLow 34` fails / `36` passes;
   `Perf.6M -25` passes) to lock them under CI.
4. (Optional) **W3-in-tracker** integration (source=W3, ACTIVE-W3) — proposed in the old handoff, never committed.

## 10. How to run

- **Live screens:** `/saudi-stage2`, `/saudi-wave2`, `/saudi-wave3`, `/saudi-track` (slash commands; MCP
  screen → node helper → print; optional ingest into `.claude/outputs/saudi-tracker.jsonl`).
- **Research conformance:** `python research/spec/conformance/rule_runner.py`,
  `python research/spec/conformance/methodology_parity.py`, `python -m research.engine.selftest_screen`,
  `python -m research.backtest.selftest_{tracker,replay,rigor,robust,regime,lifecycle,...}`.
- **Backtests:** `python -m research.rigor_run|robust_run|regime_run|lifecycle_run|replay_run
  research/panel/tadawul_2026-06-28.parquet`.
- **Experiments (hypotheses only):** `python -m research.experiments.w1_replay_60d
  research/panel/tadawul_2026-06-28.parquet` (and `w1_variant_replay`, `w1_p6m_variants`, `wave_start_*`,
  `ext_cap_*`).
