# Documentation Architecture

Status: governing model for this repository. Corrected 2026-07-02.
This document is the single home of the **documentation-governance contract** (registered in
§5). It governs where documentation facts live; it has no second, free-floating home.

## 1. Core principle (scoped)

**Single Source of Truth (SSOT):** every *living* fact has exactly one maintained authoritative
home. All other documents reference that home; they never restate it. A duplicated living fact
is a design error, not a convenience.

SSOT is strict for **living** facts only. **Point-in-time** facts (dated observations and
session state) are immutable-when-dated: never updated, only superseded by a newer dated
artifact, and therefore exempt from the single-home rule.

The architecture is two axes: **fact type × lifetime**. Lifetime is binary — Living or
Point-in-time. Parentheticals (e.g. "Living (append-only)") are qualifiers, not a third value.

## 2. Definitions

- **Canon** — the authoritative Definition layer: the machine-readable, executable source of
  truth for every feature and rule (`features.yaml`, `rules.yaml`, versioned by `VERSION`,
  proven by the golden vectors). Canon wins all semantic conflicts. Code that implements canon
  (the live TS screener, the live JS scripts) is a conformant *implementation*, not canon.
- **Living fact** — must stay true over time. Maintained; single home.
- **Point-in-time fact** — true as of its date. Not maintained; superseded, never edited.

## 3. Fact types

| Fact type | Lifetime | What it is |
|---|---|---|
| Definition | Living | A feature or rule specification (canon) |
| Contract | Living | A guarantee conformance/testing must hold (domain-scoped; may have several instances, each single-homed) |
| Rationale | Living | Why the system is shaped the way it is |
| Decision | Living (append-only) | A methodology choice and its justification |
| How-to | Living (local) | Operational instructions for a component |
| Finding | Point-in-time | A dated empirical result from an experiment/audit |
| Data/State | Living (machine-maintained) | A stateful artifact that is the truth of its own domain |
| Session state | Point-in-time | What the current work session needs to know |

## 4. Authority classes

- **Authoritative** — the single home of a living fact; may be cited, never contradicted.
- **Operational** — reference-only; points at authoritative homes, never restates values.
- **Data/State** — maintained and authoritative *within its own domain*; produced and updated
  only by the process that owns it; never hand-edited.
- **Report** — dated, disposable point-in-time output; true when dated, not maintained.
- **Session** — ephemeral; safe to overwrite or delete.

## 5. Fact-type → single home (the binding table)

Markers: **[current]** exists today · **[target]** to be created · **[widen]** exists, scope
change pending.

Contract and How-to are **domain-partitioned**: multiple instances, each with exactly one home.
`ARCHITECTURE.md` (Rationale) is the shared umbrella for the contracts — now cited by all three
methodology contracts. There is no single "Contract root" (verified empirically 2026-07-02 — the
three methodology contracts defer to none of each other, only up to the rationale umbrella).

| Fact type | Authority | Single authoritative home | Status |
|---|---|---|---|
| Definition | Authoritative | `research/spec/features.yaml` + `rules.yaml` (+ `VERSION`, `vectors/`) | [current] |
| Contract — methodology-change | Authoritative | `research/spec/TESTING.md` | [current] |
| Contract — engine↔TV conformance | Authoritative | `research/validation/CONFORMANCE.md` | [current] |
| Contract — golden-vector runner | Authoritative | `research/spec/conformance/runner_contract.md` | [current] |
| Contract — documentation-governance | Authoritative | `DOCUMENTATION.md` (this file) | [current] |
| Rationale | Authoritative | `research/ARCHITECTURE.md` (system) · each dir `README.md` (local, links up) | [current] |
| Decision | Authoritative | `research/spec/decisions.md` (date-keyed, append-only) | [current] |
| How-to | Operational | the component's own doc (`CLAUDE.md`, `.claude/commands/*`, per-dir `README.md`, `docs/*`) | [current] |
| Finding | Report | its own dated report (`RIGOR_RESULT.md`, `data-source/*`) | [current] |
| Data/State | Data/State | the panel, the tracker ledger, the ingest manifests | [current] |
| Session state | Session | `HANDOFF.md`, `SESSION_START.md` | [current] |

Canon is the gate: because Definition has one enforced home, every Operational and Session doc
can safely be reference-only.

## 6. Seam rule (how a fact moves over its lifetime)

```
Finding            Decision              Definition            Session
(Report owns   →   (log references   →   (canon edited via  →  (HANDOFF summarizes
 the numbers)       report; records       promotion path +      current state by
                    choice + validation   vectors together)     reference)
                    status ONLY —
                    never restates
                    numbers)
```

Rule: **the Report owns the numbers; the Decision references the report and records only the
choice and its validation status; canon holds the resulting definition; Session points at
canon.** A number is written once, at its origin, and cited everywhere else.

**Comparability coordinate.** A backtest or Report is identified by
`(spec_version, latest-methodology-decision-ID)` — the feature-spec it computed under, and the
newest Methodology entry in force (`decisions.md`, IDs `D-YYYY-MM-DD-NN`). Future Reports **must
record both**. `spec_version` alone is insufficient: Methodology decisions (rule
thresholds/structure) move outcomes without moving `spec_version`. Governance decisions do not
affect comparability. **Type test:** *could this entry change which names pass on any date?* Yes
→ Methodology, else Governance. (Basis: `decisions.md` D-2026-07-02-01.)

## 7. How to place a new fact (decision procedure)

1. **Lifetime?** True-when-dated, or must-stay-true?
   - *Point-in-time* → a dated **Report** or **Session** artifact. Write it dated; never update
     it; supersede with a new dated artifact. Stop.
   - *Living* → continue.
2. **Which living type?**
   - a feature/rule value → **Definition** → canon.
   - a maintained stateful artifact → **Data/State** → its store.
   - a choice + justification → **Decision** → the decision log (append).
   - why the system is shaped this way → **Rationale** → `ARCHITECTURE.md` if system-wide, else
     the local `README` (link up).
   - a conformance/testing guarantee → **Contract** → the contract for that *domain* (§5).
   - how to run/operate → **How-to** → the component's own doc.
3. **Does a home already own it?** If yes, **reference** it — do not restate. About to write a
   number that lives in canon? Cite canon instead.
4. **Two homes seem to claim it?** Apply the **merge test**: two documents may exist separately
   iff they differ in fact type OR lifetime OR authority class OR domain/scope. **Valid domains
   are exactly those enumerated in §5**; introducing a new Contract (or How-to) domain requires a
   new §5 row, which is a governance change requiring a Decision entry. If all four coordinates
   match → merge.

## 8. Maintenance schedule

| Class | Who/when updates it | Discipline |
|---|---|---|
| Definition (canon) | On an approved methodology change, via the promotion path (edit canon + vectors together; parity gate enforces JS≡canon) | A change requires a Decision entry |
| Contract | On a governance change; conformance runners updated in the same change | Rare, deliberate |
| Rationale | When the design changes | Slow-moving |
| Decision log | A new entry on **every** approved methodology **or governance** decision (a Governance entry — e.g. D-2026-07-02-01 — is in scope of its own log) | Append-only; never edited retroactively |
| How-to | In the same change that alters the component's behavior | Reference-only for values |
| Data/State | By the pipeline/ingest/tracker that owns it; provenance in manifests | Never hand-edited |
| Report | Written once, dated | Never maintained; records `(spec_version, latest-methodology-decision-ID)`; superseded by a newer report |
| Session | `HANDOFF` overwritten each session; `SESSION_START` a stable pointer | Disposable |

## 9. State (as of 2026-07-02, Step 4 complete)

- **Contract root (Step 2, verified):** no single root; the three methodology contracts are
  domain-parallel and single-homed, all under the `ARCHITECTURE.md` rationale umbrella (now cited by
  all three — the optional item below is done).
- **SSOT offenders — fixed:** the TASI-W1/TASI-W2/TASI-W3 param tables in `.claude/commands/saudi-stage2.md`,
  `saudi-wave2.md`, `saudi-wave3.md` and the gate-values list in `HANDOFF.md §2` now reference
  `rules.yaml` and restate no thresholds. **Correction to the earlier draft:** `saudi-momentum` is
  **not** an offender — it is not in `rules.yaml`; its params are owned by its own command file. And
  `docs/saudi-commands.md` was **not** clean — it duplicated `/saudi-momentum`'s params — and is now a
  thin index.
- **Command surfaces consolidated:** `.claude/commands/*.md` authoritative; `docs/saudi-commands.md`
  a thin index of links.
- **README versioning reconciled:** `research/spec/README.md` §Versioning + §Checklists now match
  `decisions.md` D-2026-07-02-01 (feature-spec `VERSION` bump vs rule Methodology Decision).
- **Rationale umbrella wired (optional item, done):** `TESTING.md`, `CONFORMANCE.md`, and
  `runner_contract.md` all now cite `ARCHITECTURE.md`.
- **Net effect on the permanent surface:** **+1** permanent authoritative doc (`decisions.md`), **−1**
  dead session artifact (the stale `Operational Handoff …md`). **Net file count flat**; permanent
  authoritative docs rise by one; clutter falls.
- **Known residual duplications:** (a) each command's **Step 2** server-side filter values remain as
  `(default N)` annotations (full de-duplication — the command reading defaults from `rules.yaml` at run
  time — is deferred as a live-product behavioral change needing its own review). **Now guarded:** the
  Tier-1 SSOT lint (`methodology_parity.py`, D-2026-07-02-03) checks these annotations against `rules.yaml`
  in CI, so a canon change not mirrored here fails the gate.
  *(Resolved 2026-07-02: `rules.yaml`'s inline change-history comments now point to `decisions.md` IDs;
  the residual prose defaults in the command docs were swept; `HANDOFF.md` rewritten to summarize by
  reference.)*
```
