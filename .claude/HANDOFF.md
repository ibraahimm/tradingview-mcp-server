
# HANDOFF — TradingView MCP + Saudi Wave Screening + Research Platform

**Updated:** 2026-07-05 (session close) · **Branch:** `feat/saudi-stage2-screen` · **HEAD:** see
`git log --oneline -15` (this session: the **TASI-W2 guardrail widening promotion** (D-2026-07-05-01,
commit `325fc66`, CI green), the canon-view generator **promoted to a tracked script** with a
professional XLSX layout, and three live runs — `/tasi-w2` ×2, `/tasi-w1` ×1 — that pushed the
tracker cohort to 45 symbols / **16 PROMOTED W1→W2**). All work committed and pushed to `mine`.

> This file is a **map, not a substitute** for the repo. The repository is the source of truth. It is
> **Session state** (disposable, per [`/DOCUMENTATION.md`](../DOCUMENTATION.md)) — it summarizes by
> reference and restates no canonical numbers. To continue in a new chat, use `.claude/SESSION_START.md`,
> which points here plus at `/DOCUMENTATION.md`, `research/ARCHITECTURE.md`, `research/spec/TESTING.md`,
> `research/spec/rules.yaml`, `research/spec/decisions.md`, `.claude/commands/tasi-*.md`, and `git log`.

---

## 1. What this repo is (three subsystems)

1. **TS MCP server + CLI** (`src/`) — the TradingView screener wrapper (unchanged core).
2. **Saudi wave screening — the live product** (`.claude/commands/` + `.claude/scripts/`) — on-demand
   slash commands `/tasi-w1`, `/tasi-w2`, `/tasi-w3`, `/tasi-track`, each = MCP screen → node helper →
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
  `offLow`, and Perf gates. **Untouched this session.**
- **TASI-W2** (`/tasi-w2`) — structural continuation screen (`close>EMA60`, the EMA21/EMA60 coil, the
  EMA21 reclaim) with two lightweight guardrails (Perf.1M ceiling + negative Perf.1Y floor,
  D-2026-07-04-01). **This session both guardrail bounds were WIDENED** — same predicates, looser
  bounds (D-2026-07-05-01; values in `rules.yaml`). Funnel stays 16 steps. The W2 definition has now
  moved **four times** since 2026-07-03 — see §5 comparability warning.
- **TASI-W3** (`/tasi-w3`) — mature re-coil near highs: `close>EMA200`, coil, capped EMA21 extension
  (`ext21_max`), `nrHi` band, `Perf.3Y` min discriminator. **Untouched all session.**
- **Tracker** (`/tasi-track`): committed methodology is **TASI-W1/TASI-W2 only**. States
  `ACTIVE-TASI-W1/W2`, `GRAD★`, `FAILED`, `STALE`, `EXPIRED`; badges `NEW/PROMOTED/nearATH`. Lifecycle
  thresholds owned by `.claude/scripts/tasi-track.js` (not `rules.yaml`). Cohort as of 2026-07-05:
  **45 symbols / 223 events, 16 PROMOTED W1→W2, 3 FAILED** (2250, 4040, 8100 — 8100 failed the same
  day it promoted).

## 3. Research platform (`research/`)

- **`spec/rules.yaml`** — canonical rule definitions (single source of truth; parity-locked to live JS).
- **`engine/`** — polars feature engine + `rules.py` (`evaluate_frame(rule, df, params_overrides)`).
- **`backtest/`** — event_study, governance, rigor, robust, regime, lifecycle, tracker (faithful JS
  port), replay; each with a `selftest_*` CI gate.
- **`spec/conformance/`** — `reference_runner`, `rule_runner`, **`methodology_parity`** (live JS ↔
  rules.yaml params + Tier-1 SSOT lint on command-doc Step-2 `(default N)` annotations), and — new
  this session — **`gen_canon_view.py`** (the tracked canon-view generator; see §4).
- **CI:** `.github/workflows/research-ci.yml` — green through the `325fc66` promotion run.
- **Reports (dated, point-in-time):** `RIGOR_RESULT.md`, `reports/canonical-rename-2026-07-02.md`,
  `reports/w2-gates-offlow30-2026-07-03.md`, `reports/w2-guardrails-restore-2026-07-04.md`,
  `reports/w2-below95-2026-07-04.md`, **`reports/w2-guardrails-widen-2026-07-05.md`** (this session).

## 4. Governance & documentation architecture — READ THIS

- **Methodology change convention** (`research/spec/TESTING.md`): official methodology lives ONLY in
  `rules.yaml` + live JS + docs, parity-locked; experiments are override-only hypotheses; promotion =
  canon + JS + docs + vectors together, decision-logged, forward-tested first.
- **Documentation architecture** ([`/DOCUMENTATION.md`](../DOCUMENTATION.md), D-2026-07-02-02): one home
  per fact; the decision log is append-only; `spec_version` versions the feature spec only
  (D-2026-07-02-01).
- **Comparability coordinate is now (`spec_version 1.0.0`, `D-2026-07-05-01`).** Any W2
  backtest/Report older than 2026-07-05 was measured under a different W2 definition and does not
  transfer (each decision entry says so explicitly).
- **Generated-Canon-view convention** (memory `generated-canon-view-convention`): any artifact derived
  from `rules.yaml` must carry a self-describing scope banner + generator-proven completeness checks.
  **The generator is now a tracked script** — `research/spec/conformance/gen_canon_view.py` (auto
  date/commit defaults; asserts its own completeness; professional XLSX layout: frozen styled headers,
  per-rule banding, autofilter, PASS-highlighted checks sheet). Run it after ANY canon change; the
  artifacts `.claude/outputs/tasi-rules-comparison.{md,xlsx}` stay gitignored outputs. Tooling only —
  not a CI gate, no decision entry (outputs-only convention, same basis as the 2026-07-03 adoption).

## 5. Key findings (so you don't re-derive them)

Pre-rename findings (RIGOR_RESULT era): TASI-W1 = TIMING/recall, no selection edge; old TASI-W2 had a
real NORMAL-regime selection edge not cleanly surviving ~31 bps; **TASI-W3 @120d = the one full-gauntlet
survivor** (still needs walk-forward + OOS); W1→W2 is the tradeable refinement.

W2 evidence chain 2026-07-03 → 07-05 (Reports in `research/reports/`, all pooled 20y, one vintage):
- **Momentum-gate removal (D-2026-07-03-02): the removed gates were LOAD-BEARING**; adopted anyway as
  an owner design decision, evidence recorded separately.
- **Guardrail restoration (D-2026-07-04-01): recovers part, not all, of that edge.**
- **offlow 35→30 / below_max 80→95 (D-2026-07-03-02 / D-2026-07-04-02): return-neutral recall widenings.**
- **Guardrail widening (D-2026-07-05-01, this session): recall widening (~11% more signals) with MILD
  per-signal dilution, worst at 120d** — one class below return-neutral; numbers in
  `reports/w2-guardrails-widen-2026-07-05.md`. Adopted by owner directive with evidence recorded.

Live confirmation of lifecycle continuity (2026-07-05 runs): roughly half of the day's W2 survivors
were admissions the widened guardrails newly allow; 7 W1→W2 promotions were recorded in one day; the
best cohort gainers are all PROMOTED journeys.

## 6. Methodology change history

All in [`research/spec/decisions.md`](../research/spec/decisions.md) — the single home. Recent:
command rename (D-2026-07-03-01); W2 simplification + offlow (D-2026-07-03-02, adverse evidence
recorded); W2 guardrails restored (D-2026-07-04-01); W2 depth widening (D-2026-07-04-02); **W2
guardrails widened (D-2026-07-05-01, this session — annual weakness filter and short-term extension
ceiling both relaxed; `w2_defaults` golden-vector boundary rows re-pinned alongside).**

## 7. Data

- **`research/panel/tadawul_2026-06-28.parquet`** — the working panel. **GITIGNORED, never committed.**
  Vintage 2026-06-28: 951,419 rows / 291 securities; manifest committed in `research/ingest/manifests/`.
- Ledger `.claude/outputs/saudi-tracker.jsonl` (Data/State; 45 symbols / 223 events as of 2026-07-05).

## 8. Git / push setup

- Remote **`mine` = `git@github.com:ibraahimm/tradingview-mcp-server.git` (SSH)**; push with
  `git push mine feat/saudi-stage2-screen`. `origin` = fork, not for push.
- **Never commit `package-lock.json`.** `.claude/` is gitignored → `git add -f` for its files.
- **Canon (`features.yaml`, `rules.yaml`, `VERSION`) changes only with separate explicit approval.**
- **User-machine / chart-link note** (memory `wsl-tradingview-app-link-wiring` — READ IT before ever
  touching link formats): scripts emit `https://www.tradingview.com/chart/?symbol=EXCHANGE%3ACODE`
  (final form, `0cff752`) — **never change this format again**. `~/.local/bin/tvopen <code>` is the
  reliable zero-click opener; `~/.local/bin/wslopen` is `$BROWSER`.

## 9. Open items / next steps

1. **TASI-W3 @120d walk-forward** (confirm pre-2020, not just recency) + true OOS on a future vintage —
   the top research item, still untouched by all the W2 changes.
2. **Re-baseline W2 analytics**: the W2 definition moved four times 2026-07-03/04/05; any new W2
   backtest must pin (`1.0.0`, `D-2026-07-05-01`) and must not be compared to earlier W2 numbers.
   Watch the 120d dilution recorded in D-2026-07-05-01 — if it matters live, rollback is a single
   revert of `325fc66`.
3. (Optional) **TASI-W3-in-tracker** integration — proposed long ago, never committed.
4. (Deferred) **Command Step-2 → read defaults from `rules.yaml` at run time** — removes the last
   runtime canon duplication (currently CI-guarded, not eliminated).
5. (Deferred) **Tier-2 SSOT lint.** *(The canon-view generator promotion is DONE this session — §4.)*
6. **OPEN (environment, not repo): Shift+Click on chart links corrupts under tmux 3.2a.** Prepared
   experiment (source-build tmux 3.5a + `terminal-features ",*:hyperlinks"` + OSC-8 smoke test) —
   **still not run**. Facts + confidence assessment recorded in the 2026-07-04 HANDOFF (git history,
   `1c47ec7`) and memory `wsl-tradingview-app-link-wiring`. Daily workaround: `tvopen`. NO repo
   changes for this — the emitted format is proven correct.
7. (Low priority) Bump CI action versions (Node 24 warnings); `research-ci` paths-filter means
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
- **Canon-view regen (after any canon change):** `python research/spec/conformance/gen_canon_view.py`.
- **Backtests:** `python -m research.{rigor_run,robust_run,regime_run,lifecycle_run,replay_run} research/panel/tadawul_2026-06-28.parquet`.
- **Experiments (hypotheses only):** `python -m research.experiments.{w1_replay_60d,w1_variant_replay,w1_p6m_variants,wave_start_study,w2_momentum_gate_removal,offlow30_promotion_test,w2_guardrails_restore_test,w2_below95_test,w2_guardrails_widen_test} research/panel/tadawul_2026-06-28.parquet`.
- **Open a chart on this machine:** `tvopen <code>` (defaults to TADAWUL).
