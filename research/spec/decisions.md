# Methodology Decision Log

Append-only, date-keyed record of methodology and governance **Decisions** (see the Decision
fact type in [`/DOCUMENTATION.md`](../../DOCUMENTATION.md) §3 and the seam rule §6). This is the
single authoritative home of the "why did the methodology change, and was it validated" fact.

**Rules of this log**
- **Append-only.** Never edit or delete a recorded entry; supersede it with a newer entry.
- **Choice + validation status only.** Numbers live in their Reports; canon (`rules.yaml`,
  `features.yaml`) holds definitions. Cite — never restate — a value here.
- **ID** = `D-YYYY-MM-DD-NN` (`NN` = that day's sequence). IDs are stable and citable.
- **Type** = `Methodology` — can change any screen/backtest outcome (thresholds, structure,
  feature use) and therefore **moves** the comparability coordinate — vs `Governance` — changes
  how the repo is run or documented, and **never** moves an outcome or the coordinate.
  **Assignment test:** *could this entry change which names pass on any date?* Yes → Methodology.
- **Comparability coordinate.** A backtest/Report is identified by
  `(spec_version, latest-Methodology-entry-ID)`. Governance entries do not affect comparability.

Entry schema: **ID · Date · Type · Choice · Validation status · Evidence (by reference) ·
Relations · [backfill marker]**.

---

## D-2026-07-02-01 · 2026-07-02 · Governance

**Choice.** `spec_version` versions the **feature spec only** (`features.yaml` algorithms +
bindings — the computational identity of the panel, validated by `vectors/`, requiring a panel
rebuild on change). Rule **threshold and structural** changes in `rules.yaml` are **not**
`spec_version` bumps; they are **Methodology Decisions recorded in this log** (and
`rule_vectors/` when a boundary case moves).

**Clause — `rules.yaml` `spec_version` field.** The `spec_version` currently carried in
`rules.yaml` is reinterpreted as a **feature-spec compatibility pointer** ("the feature-spec these
rules bind to"), not a methodology version. This is an interpretation only; **no canon file is
edited**.

**Ratification.** The four prior methodology changes below (`D-2026-06-30-01/02`,
`D-2026-07-01-01/02`) occurred before this resolution and are **ratified as correct, not
violations**: each left every computed feature value and every feature golden-vector unchanged,
so no bump was ever due.

**Validation status.** Governance decision; reversible by a superseding entry. A future
machine-checkable methodology version (`rules_version`) would edit `rules.yaml` and requires
separate approval — explicitly **not** adopted here.

**Evidence.** `/DOCUMENTATION.md` §2/§5/§6; `research/spec/README.md` §45–53 (supersedence note
added at §49; full reconciliation pending Step 4); empirical check that `VERSION` remained
unchanged across the four prior changes.

**Relations.** Ratifies D-2026-06-30-01, D-2026-06-30-02, D-2026-07-01-01, D-2026-07-01-02.

---

## D-2026-07-02-02 · 2026-07-02 · Governance

**Choice.** Adopt [`/DOCUMENTATION.md`](../../DOCUMENTATION.md) (model **C**) as the repository's
governing documentation architecture: the **fact type × lifetime** axes, the five authority classes,
the **§5 single-home table**, and the **§6 seam rule**. All documentation is reviewed and created
against it from now on (its §7 "how to place a new fact" procedure is the operative test).

**Validation status.** Governance; adopted after a multi-step documentation-architect review that
corrected an earlier draft on six substantive defects and verified the Contract root empirically.
Reversible by a superseding entry.

**Evidence.** `/DOCUMENTATION.md`; this log; the documentation-architecture pointer in
`research/spec/README.md`.

**Relations.** Governs the homes recorded by every entry in this log.

---

## D-2026-07-02-03 · 2026-07-02 · Governance

**Choice.** Adopt the **Tier-1 SSOT lint**: extend `methodology_parity.py` to check each command doc's
Step-2 server-side `(default N)` annotations against `rules.yaml`, closing the unguarded duplication that
Step-4 verification surfaced. **Tier-2** (a general canon-number-outside-canon scanner with a marker
allowlist) is **deferred, not rejected** — to be revisited only if reference-only documentation drift recurs.

**Validation status.** Implemented and green (W1 3 / W2 9 / W3 0 Step-2 defaults == canon); a negative test
confirms injected drift fails the gate (non-zero exit). Runs in the existing CI parity step. Reversible.

**Evidence.** `research/spec/conformance/methodology_parity.py`; `/DOCUMENTATION.md` §9 (residual (a) now
guarded).

**Relations.** Enforces the anti-duplication invariant of D-2026-07-02-02 (the documentation architecture).

**Addendum (2026-07-02).** Hardened with per-rule minimum annotation counts (`MIN_DOC_DEFAULTS`:
W1≥3 / W2≥9 / W3≥0) so a silently removed annotation **fails** the gate rather than shrinking coverage.
W3's Step-2 was verified to contain no canon-owned values (placeholders only) — its `0` is complete, not a gap.

---

## D-2026-07-02-04 · 2026-07-02 · Governance

**Record (CI outage).** The `research-ci` workflow file carried an invalid YAML step name — line 96's
`name:` was an unquoted plain scalar containing a colon-space (`… generation: schema/cadence/first-stamp`),
which GitHub rejects as "Invalid workflow file" at parse time (no job executes). The invalid line was
**introduced at `7908f7b`** (2026-06-29), but per the **GitHub Actions history the first failing run was
#18, triggered by `e7bd6ef`**. So the **CI enforcement gap began at `e7bd6ef` (run #18, ~2026-07-01) —
predating this session — and ran until this fix (2026-07-02).** (Both commits match the workflow's
`research/**` paths filter; the earlier `7908f7b` change reached the remote in the same push batch, so #18
is the first recorded failure.) During the gap the parity/conformance gates were enforced by **documented
local runs** (cited in commit messages, e.g. `3070aa2`). This fix quotes the line-96 name; **CI enforcement
resumes at this fix.** Recorded as its own entry (not an addendum to D-2026-07-02-03) because the outage
predates the Tier-1 lint and concerns the whole CI.

**Evidence.** GitHub Actions history (run #18 = first failure, commit `e7bd6ef`);
`.github/workflows/research-ci.yml` line 96; `git blame` (introduced at `7908f7b`, 2026-06-29); local
full-suite reproduction — every step PASS.

**Restored (2026-07-02).** CI verified **green on `c565c96`**: the workflow parses and both jobs
(`foundation-gates`, `engine-conformance`) run, including the parity gate. **CI enforcement is restored;
the gap this entry records is closed.** Two non-blocking warnings remain — GitHub forcing Node 24 on
`actions/checkout@v4` / `setup-python@v5` / `setup-node@v4` — tracked as low-priority CI hygiene in
HANDOFF §9; no change made.

---

## D-2026-07-02-05 · 2026-07-02 · Governance

**Choice (Canonical Rename).** The methodology waves are renamed to canonical identifiers
**`TASI-W1` / `TASI-W2` / `TASI-W3`** (formerly `W1/W2/W3`) everywhere they are the *identity*:
`rules.yaml` keys, engine/backtest/parity string keys, rule + lifecycle golden vectors, the live tracker
source tags, states (`ACTIVE-TASI-W1`), and journeys (`TASI-W1→TASI-W2`). **Behavior-preserving** — no
value/threshold/structural change, identical gates and outcomes; `spec_version` stays `1.0.0`, **no
`VERSION` bump** (a rule-identity relabel is Governance, not a feature change; the D-2026-07-02-01 test —
"could this change which names pass?" — is **No**).

**Sub-decisions recorded (so they don't live only in the conversation):**
1. **Fully-canonical labels** — `TASI-Wn` is used in source tags, states, and journeys (not a display
   label). Any later display truncation is a render-only decision, not a canon change.
2. **Command names kept** — `/saudi-stage2` `/saudi-wave2` `/saudi-wave3` `/saudi-track` are unchanged
   (user-facing Operational tokens); each command doc **and** the `docs/saudi-commands.md` index carry a
   `Canonical rule: TASI-Wn` mapping. Renaming commands is a separate future UX decision.
3. **Lowercase internal tokens** (`w1_pass` schema field, `entered_w1`/`has_w1` variables, `w1_defaults`
   fixture-dir names) are implementation, not the canonical surface, and are left unchanged.

**Report-annotation clause (governance).** A dated **Report** (e.g. `RIGOR_RESULT.md`) may carry a
clearly-labelled **editorial annotation that is a provenance pointer only** (e.g. "W1 was renamed
TASI-W1; see D-2026-07-02-05") without breaching its point-in-time immutability, provided it adds no new
finding and changes no recorded result. This legalises the one-line note added to `RIGOR_RESULT.md`.

**Historically unchanged (point-in-time):** the `RIGOR_RESULT.md` body and all prior decision entries
(D-2026-06-30-01 … D-2026-07-02-04) keep `W1/W2/W3` as true-when-written; only a provenance annotation
was added to the Report.

**Validation status.** All 17 CI/conformance gates green on the exact committed tree (itemised in the
commit message), incl. `rule_runner`, `methodology_parity` (JS + command-doc defaults == rules.yaml on the
new keys), and `selftest_tracker` (Py == golden == live JS). The live tracker ledger was migrated with a
proven before/after `/saudi-track` continuity diff (same symbols, same journeys relabelled, same states),
the migration script is idempotent (second run a no-op), and a renamed experiment smoke-run confirmed
`rules["TASI-W1"]` resolves against the panel.

**Canon authorization.** Executed under the scoped, single-commit `rules.yaml` **key-rename** approval
(now spent). `features.yaml` and `VERSION` untouched.

**Rollback.** `git revert <commit>`; restore the live ledger from `saudi-tracker.jsonl.bak-2026-07-02`.

**Evidence (addendum 2026-07-02).** Execution report (dated Report, per the seam rule):
[`research/reports/canonical-rename-2026-07-02.md`](../reports/canonical-rename-2026-07-02.md). Commit `a1915b0`.

---

## D-2026-07-03-01 · 2026-07-03 · Governance

**Choice (Command Rename).** The operational slash commands are renamed to lowercase forms of the
canonical rule identifiers — `/saudi-stage2` → **`/tasi-w1`**, `/saudi-wave2` → **`/tasi-w2`**,
`/saudi-wave3` → **`/tasi-w3`**, `/saudi-track` → **`/tasi-track`** — as a **clean replacement, no
alias/transition period**. The rename covers the whole operational layer in one increment so the
incoherence does not move down a level: command docs, the live scripts
(`.claude/scripts/tasi-w1.js`, `tasi-w2.js`, `tasi-w3.js`, `tasi-track.js`), and the output CSV names
(`.claude/outputs/tasi-w1.csv`, `tasi-w2.csv`, `tasi-w3.csv`). `/saudi-momentum` is **unchanged** (it
predates the wave methodology and is not in `rules.yaml`). The tracker ledger
`.claude/outputs/saudi-tracker.jsonl` keeps its name: it is a Data/State artifact (not a CSV
deliverable), referenced by the D-2026-07-02-05 rollback backup; renaming data is out of this
decision's scope.

**Supersedes** sub-decision 2 of D-2026-07-02-05 ("Command names kept"), which explicitly deferred
this as a separate future UX decision. Sub-decisions 1 and 3 of that entry stand: `TASI-Wn` remains
the canonical identifier in source tags, states, and journeys; the lowercase command tokens are the
operational surface, a case-normalization of the canonical ID, not a second vocabulary.

**Rationale.** The old names were actively misleading, not merely inconsistent: `/saudi-stage2`
(Weinstein "Stage 2") ran **TASI-W1** — the *first* wave — while `/saudi-wave2` ran TASI-W2, colliding
two vocabularies exactly on the W1/W2 boundary where the methodology distinction matters most
(TASI-W1 = timing entry, TASI-W2 = the tradeable refinement). Each command doc carried a
"Canonical rule: TASI-Wn" mapping line purely to bridge that gap. With identity-bearing surfaces
already canonical (D-2026-07-02-05), this rename is the cheap final step to one vocabulary from canon
to keyboard. No alias period: single user, and an alias file would either duplicate command content
(an SSOT violation) or add pure indirection.

**Type test.** Governance — no threshold, structural, or feature change; identical gates and
outcomes; "could this change which names pass on any date?" is **No**. `spec_version` and `VERSION`
untouched.

**Validation status.** Precondition verified before execution: a throwaway
`.claude/commands/tasi-w1.md` resolved and executed in the harness under the lowercase name.
Full local gate suite green on the main commit's tree (gates itemised in the commit message);
`methodology_parity.py` `DOCS`/`JS` paths moved in the same commit, so the Tier-1 SSOT lint stays
binding throughout. Reversible by reverting the two commits.

**Canon authorization.** A scoped, comments-only follow-up commit updates the three `# /saudi-*`
inline comments in `rules.yaml` (lines 27/63/108) to the new command names — no key, param, or
structural change (verified by parse-equality of the YAML with comments stripped). That approval is
spent on that commit; `features.yaml`, `rules.yaml`, and `VERSION` return to off-limits without
separate explicit approval.

**Historically unchanged (point-in-time):** prior decision entries, `RIGOR_RESULT.md`, and dated
reports keep the old command names as true-when-written.

**Evidence.** This entry; commit messages of the rename pair; the harness-resolution test above.

**Relations.** Supersedes D-2026-07-02-05 sub-decision 2; completes the vocabulary unification begun
by D-2026-07-02-05.

---

## D-2026-07-03-02 · 2026-07-03 · Methodology

**Choice.** Two changes to canon, adopted together as one promotion (owner directive of
2026-07-03, confirmed after evidence review):
1. **TASI-W2: remove the `p1m_min`/`p1m_max` (Perf.1M band) and `py_min` (Perf.1Y>0) gates
   entirely** — parameters and funnel predicates deleted. Perf.1M/Perf.1Y remain fetched and
   displayed as descriptors. TASI-W2's continuation/trend evidence is now expressed solely
   through structure: `close>EMA60`, the EMA21/EMA60 coil, and the EMA21 reclaim.
2. **TASI-W1 + TASI-W2: `offlow_min` 35 → 30** — a partial revert of the D-2026-07-01-01 band
   widening (which had raised the floor to 35 and was retained as return-neutral in
   D-2026-07-01-02). Values in `rules.yaml`.

**Empirical evidence (recorded distinctly from the rationale).** Forward-tested **before**
adoption on the full 20-year panel (Report:
[`research/reports/w2-gates-offlow30-2026-07-03.md`](../reports/w2-gates-offlow30-2026-07-03.md)):
- The removed TASI-W2 gates were **load-bearing for the historical per-signal edge**: with them,
  W2 was deflated-significant at 20d and net-positive at all horizons; without them the
  market-neutral excess collapses to noise and is net-negative after cost at every horizon
  (P(current>gateless) 0.84–0.97). The change **widens recall (~46% more deduped signals) at the
  cost of the measured per-signal selection edge.**
- `offlow_min` 35→30 alone is **return-neutral-to-slightly-diluting** (W2 keeps its deflated 20d
  significance; ~17% more signals; P(cur>variant) ≈ 0.53–0.73 across rules/horizons).

**Rationale for adoption (the design decision, distinct from the evidence above).** Directed by
the methodology owner as an intentional design choice, with the adverse gate-removal evidence
reviewed and acknowledged: TASI-W2 is redefined around its **structural** gates (trend +
coil + reclaim) rather than point-to-point momentum windows, and the entry band is widened for
recall. The owner accepts the loss of the historically measured per-signal edge as a trade-off
of this redefinition. This entry supersedes the "confirmed uptrend (Perf.1Y>0) inversion" as
part of TASI-W2's definition; prior descriptions of that inversion remain true-when-written.

**Validation status.** Forward-tested before adoption; the test result was **adverse** for
change 1 and **neutral** for change 2 (see the Report). Adopted notwithstanding, by explicit
owner decision. Any prior W2 findings (e.g. the RIGOR_RESULT selection-edge finding) were
measured under the pre-change definition and do not transfer to the new TASI-W2.

**Comparability coordinate.** Reports/backtests after this entry are identified by
(`spec_version 1.0.0`, `D-2026-07-03-02`). No `VERSION` bump (rule change, not feature change —
D-2026-07-02-01).

**Evidence.** The Report above; `research/experiments/w2_momentum_gate_removal.py`,
`research/experiments/offlow30_promotion_test.py` (override-only drivers, committed with this
change); the promotion commit (canon + JS + docs + vectors + parity minimums together).

**Relations.** Partially reverts D-2026-07-01-01 (offlow floor); supersedes-in-definition the
TASI-W2 trend-inversion described in D-2026-07-01-01/02 context; evidence method follows
D-2026-06-30-01 (the ext60 precedent — there the tested gate was inert and removed; here the
tested gates were load-bearing and removed by design).

**Rollback.** `git revert` the promotion commit.

---

## D-2026-07-04-01 · 2026-07-04 · Methodology

**Choice.** **Refinement of the D-2026-07-03-02 TASI-W2 simplification** (owner directive of
2026-07-04): restore two **lightweight guardrails** to TASI-W2 — `p1m_max` (predicate
`perf_1m lt @p1m_max`: Perf.1M below the ceiling, no lower band) and `py_min` (predicate
`perf_1y gt @py_min`, now a *negative* floor rather than the old confirmed-uptrend
requirement). **`p1m_min` remains removed.** Values in `rules.yaml`. Intent: avoid overly
extended short-term moves (Perf.1M ceiling) and severe longer-term weakness (Perf.1Y floor)
while keeping the recall-oriented, structurally-gated W2 of D-2026-07-03-02.

**Empirical evidence** (Report:
[`research/reports/w2-guardrails-restore-2026-07-04.md`](../reports/w2-guardrails-restore-2026-07-04.md),
tested **before** adoption): the guardrails improve on the gateless current rule at every
horizon (P(variant>current) 0.65–0.81; net back to break-even-or-positive) while dropping only
~9% of deduped signals. They recover **part, not all**, of the pre-simplification per-signal
edge (the old full gates remain deflated-significant at 20d; the guardrail variant is
directionally positive but not deflated-significant).

**Rationale for adoption.** Owner design decision consistent with the evidence direction: a
quality floor that trims only the extended-move and severe-weakness tails, priced at minimal
recall cost, refining — not reverting — the 2026-07-03 structural redefinition.

**Validation status.** Forward-tested before adoption; **favorable vs current canon**, partial
recovery vs the pre-simplification rule; not deflated-significant on its own. Pooled 20-year,
one vintage; no regime split/OOS.

**Comparability coordinate.** Subsequent Reports/backtests are identified by
(`spec_version 1.0.0`, `D-2026-07-04-01`). No `VERSION` bump.

**Evidence.** The Report above; `research/experiments/w2_guardrails_restore_test.py`
(candidate-rule driver, committed); the promotion commit (canon + JS + docs + vectors + parity
minimums together).

**Relations.** Refines D-2026-07-03-02 (partially restores what it removed, in weakened
guardrail form: Perf.1M ceiling only, Perf.1Y floor at −20 instead of 0); evidence method
follows D-2026-06-30-01.

**Rollback.** `git revert` the promotion commit.

---

## Backfilled entries

*Recorded 2026-07-02 from commit history and reports; each keeps its original decision date.*

### D-2026-06-30-01 · 2026-06-30 · Methodology · [backfilled 2026-07-02]

**Choice.** Removed the extension cap (`ext60_max` on W1, and the corresponding W2 `ext21` upper
cap); the extension metric is retained as a **tracker descriptor only**, no longer a gate.

**Validation status.** Statistically **inert** in a pooled 20-year rigor re-test; a day-by-day
path review of the recent window showed the cap cut as many early winners as knives. Numbers by
reference.

**Evidence.** `research/RIGOR_RESULT.md`; `research/experiments/ext_cap_paths.py`,
`ext_cap_recent.py`; commit `ae11d1d`.

### D-2026-06-30-02 · 2026-06-30 · Methodology · [backfilled 2026-07-02]

**Choice.** Raised the W1 `below_max` ceiling to admit the most-corrected deep-launch names.
Values in `rules.yaml`.

**Validation status.** Recall-oriented adoption (admits the most-corrected names); **not
independently forward-return tested**.

**Evidence.** `.claude/commands/saudi-stage2.md` (change note); `rules.yaml`; commit `ae11d1d`.

### D-2026-07-01-01 · 2026-07-01 · Methodology · [backfilled 2026-07-02]

**Choice.** Widened the W1 and W2 entry band — `offLow`, `Perf.6M`, `Perf.3Y`, and W1 `Perf.5Y`
thresholds — to a later, more-selective first-wave entry (W1) and continuation (W2). Values in
`rules.yaml`.

**Validation status.** Validated **only as more selective on a 60-day recall snapshot** at
adoption; **not** forward-return tested at that time. Superseded-in-status by D-2026-07-01-02.

**Evidence.** `rules.yaml` (canon); `.claude/commands/saudi-stage2.md`, `saudi-wave2.md`; commit
`ae11d1d`; `HANDOFF.md` §6.

### D-2026-07-01-02 · 2026-07-01 · Methodology · [backfilled 2026-07-02]

**Choice.** **Retain** the D-2026-07-01-01 parameters unchanged after forward-return testing (no
revert).

**Validation status.** Forward-return backtest found the change **return-neutral** — no
per-signal improvement versus the prior parameters across horizons. Retained as a
**selective-entry choice, explicitly not an edge-improvement claim**.

**Evidence.** `research/experiments/w1w2_param_forward_backtest.py` (Report; currently untracked).

**Relations.** Validates / follows D-2026-07-01-01.
