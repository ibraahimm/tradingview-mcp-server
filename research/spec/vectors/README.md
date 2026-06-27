# Golden Vectors — format & CI contract

A **golden vector** is a frozen `input → expected` fixture for one algorithm (`function` in
`../features.yaml`). It is the executable half of the canonical spec: every implementation must
reproduce every expected value within tolerance, or CI fails. Vectors are **language-agnostic**
(plain CSV + JSON), so the TypeScript screener and the Python engine validate against the *same*
truth.

## Layout

```
vectors/
  _schema/case.schema.json     # JSON Schema for a case manifest
  <case_id>/
    case.json                  # manifest: which function, params, files, tolerance
    input_bars.csv             # inputs (one row per bar, or a single row for per-bar exprs)
    expected.csv               # expected outputs, aligned 1:1 to input rows by `idx`
```

## `case.json` (manifest)

```json
{
  "case_id": "ema_n3",
  "spec_version": "1.0.0",
  "target": {"kind": "function", "id": "ema", "params": {"length": 3}},
  "description": "EMA recursion + first-close seed + warmup nulling, hand-computable at length=3.",
  "input_file": "input_bars.csv",
  "expected_file": "expected.csv",
  "tolerance": {"abs": 1e-9, "rel": 0.0},
  "null_token": ""
}
```

- `target.kind` is `function` (validate an algorithm) or `expr` (validate a per-bar expression set).
- `tolerance` is per-case; the **default per-field tolerances** live in `../../validation/CONFORMANCE.md`
  and a case may only *tighten* them. A value is "equal" if `abs(got-exp) <= abs OR abs(got-exp) <= rel*abs(exp)`.
- `null_token` is the CSV cell that denotes an emitted null (default empty string). An expected null
  must be matched by an emitted null (and vice-versa) — a number where null is expected is a failure.

## CSV conventions

- First column is always `idx` (0-based bar index); `date` (ISO `YYYY-MM-DD`) is present when the
  function is calendar-aware (`perf_calendar`, rolling windows).
- `expected.csv` columns are the feature/function outputs under test.
- Empty cell = null (or whatever `null_token` says).

## CI contract (enforced by `conformance/reference_runner.py`)

A build **fails** if any of the following hold:

1. **Coverage** — any `feature` in `features.yaml` references a `vectors:` id that does not exist, OR
   any non-trivial `function` has zero covering vectors. (Pure window anchors like `ath`/`high_52w`
   are covered indirectly; structural ratios via `ratios_basic`.)
2. **Conformance** — for any case, any implementation produces a value outside tolerance, a null/value
   mismatch, or a row-count mismatch.
3. **Version drift** — a case's `spec_version` does not match `../VERSION`.

The runner is invoked twice — once per implementation — through a tiny adapter that exposes the
implementation's functions under the contract in `conformance/runner_contract.md`. Both must pass.

## Adding a case

Pick the smallest input that exercises the behavior (seed, warmup, null-before-history, an exact
ratio). Hand-compute (or derive from the reference functions) the expected values, freeze them, and
reference the `case_id` from the relevant feature's `vectors:` list in `features.yaml`.
