# Canonical Specification — `research/spec/`

The **single authoritative definition** of every derived feature and screen rule. It exists so
that two implementations — the live **TypeScript** screener (production) and the **Python/Polars**
research engine (backtest) — compute *the same thing*, provably, forever.

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

- **PATCH** — clarification with no numeric change to any output (docs, comments).
- **MINOR** — a new feature/rule, or a backward-compatible addition; existing outputs unchanged.
- **MAJOR** — any change to an existing feature/rule definition that can alter a historical value.

Any MINOR/MAJOR change **must**: bump `VERSION`, add/adjust the relevant golden vector(s), and trigger
a panel rebuild under the new `spec_version` (recorded in every run manifest, see `../ARCHITECTURE.md`
§L8). Backtests are only comparable within the same `spec_version`.

## Units & null policy (read before implementing)

- Ratio-style features are emitted in **percent** (×100) to match the live screener exactly.
- Performance is **price-return**; a separate total-return series exists only for P&L simulation.
- Windows use the **exchange calendar** (`../reference/exchange_calendar`), never naive calendar days.
- Unmet preconditions emit **null** — never `0`, never a NaN sentinel. Ratios propagate null from any
  null input (e.g. `ext60` is null while `ema60` is in warmup).

## Adding or changing a feature (checklist)

1. Edit `features.yaml` (and `rules.yaml` if a rule changes). 2. Add/adjust a golden vector under
`vectors/`. 3. Bump `VERSION` per semver. 4. Implement in **both** engines. 5. CI golden-vector gate
must pass (every feature must map to ≥1 vector — see `conformance/runner_contract.md`). 6. Rebuild the
panel; note the new `spec_version` in affected runs.
