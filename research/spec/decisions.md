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
