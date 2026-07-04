
# HANDOFF — TradingView MCP + Saudi Wave Screening + Research Platform

**Updated:** 2026-07-04 · **Branch:** `feat/saudi-stage2-screen` · **HEAD:** see `git log --oneline -15`
(this session: the **command rename `/saudi-*` → `/tasi-*`**, three **TASI-W2 methodology promotions**
(gate removal → guardrails → depth widening), the tracker Jrny render wrap, the chart-link fix, and the
self-describing generated-Canon-view convention). All work committed and pushed to `mine`.

> This file is a **map, not a substitute** for the repo. The repository is the source of truth. It is
> **Session state** (disposable, per [`/DOCUMENTATION.md`](../DOCUMENTATION.md)) — it summarizes by
> reference and restates no canonical numbers. To continue in a new chat, use `.claude/SESSION_START.md`,
> which points here plus at `/DOCUMENTATION.md`, `research/ARCHITECTURE.md`, `research/spec/TESTING.md`,
> `research/spec/rules.yaml`, `research/spec/decisions.md`, `.claude/commands/tasi-*.md`, and `git log`.

---

## 1. What this repo is (three subsystems)

1. **TS MCP server + CLI** (`src/`) — the TradingView screener wrapper (unchanged core).
2. **Saudi wave screening — the live product** (`.claude/commands/` + `.claude/scripts/`) — on-demand
   slash commands `/tasi-w1`, `/tasi-w2`, `/tasi-w3`, `/tasi-track` (renamed from `/saudi-*` this
   session, D-2026-07-03-01; scripts + CSVs renamed with them), each = MCP screen → node helper →
   print. Persistent CSVs in `.claude/outputs/` (`tasi-w*.csv`); ledger stays `saudi-tracker.jsonl`.
3. **Research / backtesting platform** (`research/`, Python + polars) — answers, with rigor, whether the
   wave methodology has a real edge, and keeps the live screens honest.

## 2. The documented methodology (lifecycle)

`collapse → TASI-W1 (deep-correction first-wave ENTRY) → TASI-W2 (re-coil continuation) → TASI-W3
(mature re-coil in a normal trend)`. The **tracker** = one journey per symbol across waves.

**Current OFFICIAL gate values** — canonical in [`research/spec/rules.yaml`](../research/spec/rules.yaml)
(`TASI-W1`/`TASI-W2`/`TASI-W3` → `params`), mirrored in the live JS and parity-locked by
`methodology_parity.py`; change history in [`research/spec/decisions.md`](../research/spec/decisions.md).
**Read the numbers from `rules.yaml`; this Session doc does not restate them.**

- **TASI-W1** (`/tasi-w1`) — deep-correction first-wave entry: listing-age, `DDmax`, `belowATH`,
  `offLow`, and Perf gates. `offlow_min` lowered this session (part of D-2026-07-03-02).
- **TASI-W2** (`/tasi-w2`) — **redefined this session across three decisions**: trend/continuation
  evidence is now **structural** (`close>EMA60`, the EMA21/EMA60 coil, the EMA21 reclaim); the old
  Perf.1M band + Perf.1Y>0 inversion were removed (D-2026-07-03-02), lightweight guardrails restored
  (Perf.1M ceiling + negative Perf.1Y floor, D-2026-07-04-01), and the `belowATH` depth band widened
  for W1→W2 lifecycle continuity (D-2026-07-04-02). Funnel is 16 steps.
- **TASI-W3** (`/tasi-w3`) — mature re-coil near highs: `close>EMA200`, coil, capped EMA21 extension
  (`ext21_max` — still a W3 gate; only the W1/W2 caps were ever removed), `nrHi` band, `Perf.3Y` min
  discriminator. **Untouched all session.**
- **Tracker** (`/tasi-track`): committed methodology is **TASI-W1/TASI-W2 only**. States
  `ACTIVE-TASI-W1/W2`, `GRAD★`, `FAILED`, `STALE`, `EXPIRED`; badges `NEW/PROMOTED/nearATH`. Lifecycle
  thresholds owned by `.claude/scripts/tasi-track.js` (not `rules.yaml`). Jrny column now soft-wraps at
  `→` (render-only, `76d6d47`). Cohort as of 2026-07-04: 40 symbols, **8 PROMOTED W1→W2**.

## 3. Research platform (`research/`)

- **`spec/rules.yaml`** — canonical rule definitions (single source of truth; parity-locked to live JS).
- **`engine/`** — polars feature engine + `rules.py` (`evaluate_frame(rule, df, params_overrides)`).
- **`backtest/`** — event_study, governance, rigor, robust, regime, lifecycle, tracker (faithful JS
  port), replay; each with a `selftest_*` CI gate.
- **`spec/conformance/`** — `reference_runner`, `rule_runner`, **`methodology_parity`** (live JS ↔
  rules.yaml params + Tier-1 SSOT lint on command-doc Step-2 `(default N)` annotations, with per-rule
  minimum counts — updated alongside each promotion this session).
- **CI:** `.github/workflows/research-ci.yml` — green through run #32 (later commits touched only
  `.claude/`, outside the paths filter; the tracker gate ran green locally).
- **Reports (dated, point-in-time):** `RIGOR_RESULT.md` (pre-rename findings),
  `reports/canonical-rename-2026-07-02.md`, `reports/w2-gates-offlow30-2026-07-03.md`,
  `reports/w2-guardrails-restore-2026-07-04.md`, `reports/w2-below95-2026-07-04.md`.

## 4. Governance & documentation architecture — READ THIS

- **Methodology change convention** (`research/spec/TESTING.md`): official methodology lives ONLY in
  `rules.yaml` + live JS + docs, parity-locked; experiments are override-only hypotheses; promotion =
  canon + JS + docs + vectors together, decision-logged, forward-tested first.
- **Documentation architecture** ([`/DOCUMENTATION.md`](../DOCUMENTATION.md), D-2026-07-02-02): one home
  per fact; the decision log is append-only; `spec_version` versions the feature spec only
  (D-2026-07-02-01).
- **Comparability coordinate is now (`spec_version 1.0.0`, `D-2026-07-04-02`).** Any W2
  backtest/Report older than 2026-07-03 was measured under a materially different W2 definition and
  does not transfer (each decision entry says so explicitly).
- **Generated-Canon-view convention** (session memory `generated-canon-view-convention`): any artifact
  derived from `rules.yaml` must carry a self-describing scope banner + generator-proven completeness
  checks (params + funnel predicates incl. structural literals + tags). Reference artifacts:
  `.claude/outputs/tasi-rules-comparison.{md,xlsx}` (gitignored; regenerate on canon change).

## 5. Key findings (so you don't re-derive them)

Pre-rename findings (RIGOR_RESULT era): TASI-W1 = TIMING/recall, no selection edge; old TASI-W2 had a
real NORMAL-regime selection edge not cleanly surviving ~31 bps; **TASI-W3 @120d = the one full-gauntlet
survivor** (still needs walk-forward + OOS); W1→W2 is the tradeable refinement.

This session's forward tests (Reports in `research/reports/`, all pooled 20y, one vintage):
- **The removed W2 momentum gates were LOAD-BEARING** for the historical per-signal edge (net-negative
  without them); removal was adopted anyway as an owner design decision — evidence and rationale are
  recorded **separately** in D-2026-07-03-02.
- **The restored guardrails recover part, not all, of that edge** (favorable vs the gateless rule at
  every horizon; not deflated-significant alone) — D-2026-07-04-01.
- **offlow 35→30 and below_max 80→95: return-neutral recall widenings** — D-2026-07-03-02 /
  D-2026-07-04-02.

## 6. Methodology change history

All in [`research/spec/decisions.md`](../research/spec/decisions.md) — the single home. This session:
command rename (D-2026-07-03-01, Governance, supersedes D-2026-07-02-05 sub-decision 2); W2
simplification + offlow (D-2026-07-03-02, Methodology, adverse evidence recorded); W2 guardrails
(D-2026-07-04-01, Methodology, refinement); W2 depth widening (D-2026-07-04-02, Methodology,
return-neutral). Rule golden vectors were redesigned alongside (removals + boundaries pinned).

## 7. Data

- **`research/panel/tadawul_2026-06-28.parquet`** — the working panel. **GITIGNORED, never committed.**
  Vintage 2026-06-28: 951,419 rows / 291 securities; manifest committed in `research/ingest/manifests/`.
- Ledger `.claude/outputs/saudi-tracker.jsonl` (Data/State; name deliberately kept at the rename —
  D-2026-07-03-01 records why).

## 8. Git / push setup

- Remote **`mine` = `git@github.com:ibraahimm/tradingview-mcp-server.git` (SSH)**; push with
  `git push mine feat/saudi-stage2-screen`. `origin` = fork, not for push.
- **Never commit `package-lock.json`.** `.claude/` is gitignored → `git add -f` for its files.
- **Canon (`features.yaml`, `rules.yaml`, `VERSION`) changes only with separate explicit approval.**
- User-machine note (memory `wsl-tradingview-app-link-wiring`): chart links open in the TradingView
  desktop app via `~/.local/bin/{wslopen,tvopen}`; scripts emit dash-path https links (`28e477a`) —
  **do not change link formats in the scripts; the machine opener handles routing.**

## 9. Open items / next steps

1. **TASI-W3 @120d walk-forward** (confirm pre-2020, not just recency) + true OOS on a future vintage —
   the top research item, untouched by this session's W2 changes.
2. **Re-baseline W2 analytics**: the W2 definition moved three times 2026-07-03/04; any new W2
   backtest must pin (`1.0.0`, `D-2026-07-04-02`) and must not be compared to RIGOR_RESULT-era W2
   numbers.
3. (Optional) **TASI-W3-in-tracker** integration — proposed long ago, never committed.
4. (Deferred) **Command Step-2 → read defaults from `rules.yaml` at run time** — removes the last
   runtime canon duplication (currently CI-guarded, not eliminated).
5. (Deferred) **Tier-2 SSOT lint**; (optional) promote the canon-view generator from session scratch to
   a tracked script (e.g. `research/spec/conformance/gen_canon_view.py`).
6. (Low priority) Bump CI action versions (Node 24 warnings); note `research-ci` paths-filter means
   `.claude/`-only commits don't trigger CI — tracker gate must be run locally for those.

**Working-tree note (intentional — do not "clean up"):** two items stay uncommitted — a modified
`package-lock.json` (not ours; never commit) and the untracked
`research/experiments/w1w2_param_forward_backtest.py` (kept local per an earlier call; its finding is
recorded in D-2026-07-01-02). A fresh `git status` shows both; leave them.

## 10. How to run

- **Live screens:** `/tasi-w1`, `/tasi-w2`, `/tasi-w3`, `/tasi-track` (+ `/saudi-momentum`, unrenamed —
  not in canon).
- **Conformance/parity:** `python research/spec/conformance/{rule_runner,methodology_parity,reference_runner}.py`,
  `python -m research.engine.selftest_screen`, `python -m research.backtest.selftest_{tracker,replay,rigor,robust,regime,lifecycle}`.
- **Backtests:** `python -m research.{rigor_run,robust_run,regime_run,lifecycle_run,replay_run} research/panel/tadawul_2026-06-28.parquet`.
- **Experiments (hypotheses only):** `python -m research.experiments.{w1_replay_60d,w1_variant_replay,w1_p6m_variants,wave_start_study,w2_momentum_gate_removal,offlow30_promotion_test,w2_guardrails_restore_test,w2_below95_test} research/panel/tadawul_2026-06-28.parquet`.
- **Open a chart on this machine:** `tvopen <code>` (defaults to TADAWUL).
