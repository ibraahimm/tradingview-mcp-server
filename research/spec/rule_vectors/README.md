# Rule Vectors — golden fixtures for TASI-W1/TASI-W2/TASI-W3 decisions

Frozen `feature-row → expected decision` fixtures for the screen rules (`../rules.yaml`), the
rule-layer analogue of the feature golden vectors. They validate ordered predicate evaluation,
every operator (`ge/gt/le/lt/in_co/in_oo/in_cc`), null handling (`skip`/`drop`), `enabled_when`
guards, and the **first failing gate** (not just pass/fail) — so evaluation *order* is pinned.

## Layout

```
rule_vectors/<case_id>/
  case.json     # {case_id, spec_version, rule: "TASI-W1"|"TASI-W2"|"TASI-W3", params_overrides?, input_file, expected_file}
  input.csv     # one row per candidate: a `label` column + the feature columns the rule reads
  expected.csv  # label, pass (true/false), first_fail (gate feature id, empty when pass)
```

- Empty feature cell = null (exercises `null_action`).
- `params_overrides` (optional) tweaks rule params for the case (e.g. turn on the `value` floor to
  exercise `enabled_when`).
- `first_fail` is the feature id of the first enabled predicate that fails, or empty when the row
  passes — this is what pins evaluation order.

## Gate (driven by `../conformance/rule_runner.py`)

A build fails if: any case's `spec_version` ≠ `../VERSION`; the engine's `(passed, first_fail)` for
any candidate ≠ the frozen expectation; the row-wise and frame-wise (`evaluate_frame`) paths
disagree; or any rule in `rules.yaml` has zero covering cases.
