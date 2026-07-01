# Testing & methodology-change convention

This pins **how we keep the official methodology stable while leaving experimentation free**. The
dividing line is simple: **runtime override vs. file edit.**

> This is the **methodology-change contract**, one of the repo's domain-scoped contracts. Rationale
> umbrella: the three-truths model in [`../ARCHITECTURE.md`](../ARCHITECTURE.md) §2. Contract map and
> documentation architecture: [`../../DOCUMENTATION.md`](../../DOCUMENTATION.md) §5.

## The three categories

| Category | Defines/asserts | Mechanism | CI-gated | Lives in |
|---|---|---|---|---|
| **Official methodology** | *Defines* the W1/W2/W3 screens | the **files**: `research/spec/rules.yaml` + `.claude/scripts/saudi-stage2.js` / `saudi-wave2.js` (+ `.claude/commands/*.md`) | — (it is the source of truth) | spec + `.claude/` |
| **Conformance / parity** | *Asserts* the official definitions are internally consistent and the live JS matches the spec, **at default params** | golden vectors (`rule_runner`), `methodology_parity.py`, engine self-tests — **no overrides** | **Yes** | `research/spec/conformance/`, engine self-tests |
| **Experimental improvement** | *Explores* alternative thresholds / extra conditions | `evaluate_frame(rule, df, params_overrides={…})` and/or clearly-labelled **observable** candidate pre-filters — **never edits the official files** | **No** (on-demand) | `research/experiments/` |

## Two rules that make it unambiguous

1. **Experiments never edit `rules.yaml` or the live JS.** They override at runtime. Their results are
   **hypotheses**, never "the methodology." Every file in `research/experiments/` carries an EXPERIMENTAL
   banner saying so.
2. **Promotion path (experiment → official):** when an experiment earns adoption, you **edit**
   `rules.yaml` **and** the live JS **and** the docs (**and** add/update a golden vector). The parity gate
   then *forces* those to stay consistent. Examples on record: the `ext60` cap removal and `below_max`
   95→100 (2026-06-30) — both were applied to all official sources together, not as overrides.

## What `methodology_parity.py` enforces (and its current limitation)

- It compares the **parameter default values** parsed from the two live JS scripts against
  `rules.yaml`'s W1/W2 `params`, and FAILS CI on any mismatch. This prevents *silent drift* between the
  live screener and the research spec.
- It has **zero awareness** of `research/` analysis or experiment scripts, so it cannot block
  experimentation (experiments use overrides, which don't touch the compared files).
- **Limitation (not yet closed):** it checks **parameter parity, not full behavioral equivalence.** A
  change to gate *logic* (an operator, the funnel order) that doesn't change a parameter *value* would
  not be caught. Closing that needs a JS↔engine behavioral differential on shared fixtures (like the
  tracker JS↔Python differential in `selftest_tracker`). Tracked as future work.

## Reading experimental results

Anything printed by a `research/experiments/` driver is an **exploration**, not a documented result.
Do not cite it as methodology. If it matters, promote it via the path above (which makes it official,
tested, and parity-locked) — or it stays a hypothesis.
