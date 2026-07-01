# Canonical Specification — `research/spec/`

The **single authoritative definition** of every derived feature and screen rule. It exists so
that two implementations — the live **TypeScript** screener (production) and the **Python/Polars**
research engine (backtest) — compute *the same thing*, provably, forever.

> **Repository documentation architecture** — how docs are organized across the whole repo
> (fact types, the single-home rule, authority classes, the seam rule) lives in the top-level
> [`DOCUMENTATION.md`](../../DOCUMENTATION.md). This README is the *local* index for `research/spec/`.

## Why a spec at all (and why executable)

A prose definition drifts the day it is written. So the spec is **prose + an executable contract**:

| File | Role |
|---|---|
| `VERSION` | Current spec version (semver). Every result records the version it ran under. |
| `features.yaml` | Machine-readable registry: algorithms (`functions`) + named bindings (`features`) + as-of rules. |
| `rules.yaml` | W1/W2/W3 screen rules as ordered predicates over features, with threshold params + defaults. |
| `features.md` | Human narrative & rationale (this README links the concepts; the YAML is canonical). |
| `vectors/` | **Golden vectors** — input→expected fixtures both implementations must reproduce in CI. |
| `conformance/` | The CI runner contract + a runnable reference runner. |

The YAML files are **canonical**; if prose and YAML ever disagree, the YAML wins.

## The three layers

```
functions   →  features        →  rules
(algorithms)   (named bindings)    (W1/W2/W3 predicate sets)
ema(length)    ema21 = ema(21)     W1 = age≥5 ∧ perf_3m∈[5,40) ∧ … ∧ ext60≤10
perf(months)   perf_3m = perf(3)   …
```

- **functions** are parameterized algorithms — *these* are what golden vectors validate (validate
  `ema` once with `length=3`; `ema21/60/200` inherit correctness by construction).
- **features** bind a function to params (or are a pure per-bar `expr`) and define units, nullability,
  and warmup. They are the columns emitted into the panel.
- **rules** compose features into the screens' pass/fail decisions.

## Precedence (non-negotiable)

**The spec wins all semantic conflicts.** TradingView is the execution reference, not ground truth;
it is non-static and has its own conventions. When the engine and TV disagree, we do **not** edit a
definition to match TV — we record a *monitored, bounded delta* (see `../validation/CONFORMANCE.md`).
Reasons the engine may legitimately differ from TV: EMA seeding/warmup, performance-window anchoring,
corporate-action adjustment method, calendar/holiday handling, rolling-window edges.

## Versioning & change control (semver)

`spec_version` versions the **feature spec only** (`features.yaml` algorithms + bindings — the
computational identity of the panel), validated by `vectors/` and, on change, requiring a panel rebuild
(`decisions.md` D-2026-07-02-01). Scope of a bump:

- **PATCH** — clarification with no numeric change to any feature output (docs, comments).
- **MINOR** — a new feature, or a backward-compatible addition; existing feature outputs unchanged.
- **MAJOR** — a change to an existing **feature** definition that can alter a historical feature value.

Any MINOR/MAJOR **feature** change **must**: bump `VERSION`, add/adjust the relevant golden vector(s), and
trigger a panel rebuild under the new `spec_version` (recorded in every run manifest, see
`../ARCHITECTURE.md` §L8).

**Rule (`rules.yaml`) changes are different.** A change to a rule **threshold or structure** does *not*
alter any computed feature value or the panel, so it is **not** a `VERSION` bump — it is a **Methodology
Decision** recorded in [`decisions.md`](./decisions.md) (plus a `rule_vectors/` case when a boundary
moves). The `spec_version` carried in `rules.yaml` is a *feature-spec compatibility pointer* ("the
feature-spec these rules bind to"), not a methodology version. Backtest comparability is therefore two
coordinates — `(spec_version, latest-Methodology-decision-ID)` — see `../../DOCUMENTATION.md` §6.

## Units & null policy (read before implementing)

- Ratio-style features are emitted in **percent** (×100) to match the live screener exactly.
- Performance is **price-return**; a separate total-return series exists only for P&L simulation.
- Windows use the **exchange calendar** (`../reference/exchange_calendar`), never naive calendar days.
- Unmet preconditions emit **null** — never `0`, never a NaN sentinel. Ratios propagate null from any
  null input (e.g. `ext60` is null while `ema60` is in warmup).

## Changing a feature vs changing a rule (checklists)

**A feature change** (`features.yaml`): 1. Edit `features.yaml`. 2. Add/adjust a golden vector under
`vectors/`. 3. Bump `VERSION` per semver. 4. Implement in **both** engines. 5. CI golden-vector gate must
pass (every feature must map to ≥1 vector — see `conformance/runner_contract.md`). 6. Rebuild the panel;
note the new `spec_version` in affected runs.

**A rule threshold/structural change** (`rules.yaml`): 1. Edit `rules.yaml` **and** the live JS together
(`methodology_parity.py` enforces parity). 2. Add/adjust a `rule_vectors/` case if a boundary moves.
3. Record a **Methodology Decision** in [`decisions.md`](./decisions.md) — choice + validation status,
numbers by reference. 4. **No `VERSION` bump, no panel rebuild** (feature values are unchanged).
