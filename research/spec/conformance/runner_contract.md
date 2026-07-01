# Golden-Vector Runner Contract

Defines the interface both implementations expose so the **same** runner can validate each against
the **same** golden vectors. This is the bridge that keeps the TypeScript live screener and the
Python research engine semantically identical without forcing one language.

> This is the **golden-vector runner contract**, one of the repo's domain-scoped contracts. Rationale
> umbrella: the three-truths model in [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) §2. Contract map
> and documentation architecture: [`../../../DOCUMENTATION.md`](../../../DOCUMENTATION.md) §5.

## The implementation adapter

Each implementation provides a small adapter exposing its functions under stable ids:

```
FUNCTIONS = {
  "ema":           (closes: number[], params) -> (number | null)[]
  "perf_calendar": (rows: {date, close}[], params) -> (number | null)[]
  "ratios":        (row: {close, ath, low_52w, high_52w, ema21, ema60, ema200})
                       -> { ddmax, below_ath, off_low, nrhi, ext60, ema21gap, ema_comp, vs200 }
}
```

- Python engine: a module exposing `FUNCTIONS` (callables operating on Polars/py types).
- TS screener: a CLI/JSON adapter (`node adapter.js <function> <case_dir>`) emitting the same rows.
- The runner is agnostic to which side it drives; it loads each case, calls the function under its
  `target.id`, and compares to `expected.csv` within tolerance.

## Comparison rules

- Numeric equality: `abs(got-exp) <= tol.abs` **or** `abs(got-exp) <= tol.rel*abs(exp)`.
- Null equality: an expected null (per `null_token`) must be an emitted null and vice-versa.
- Shape: emitted row/column count must match `expected.csv` exactly.

## CI gate (build fails if any holds)

1. **Coverage** — every `vectors:` id referenced in `../features.yaml` resolves to an existing case
   directory; every algorithm-backed feature has ≥1 covering case.
2. **Conformance** — every case passes for **every** implementation adapter.
3. **Version** — every case's `spec_version` equals `../VERSION`.

The reference runner (`reference_runner.py`) ships a built-in reference implementation of `FUNCTIONS`
so the vectors are self-validating today (and so a new vector can be checked the moment it is written).
Production runs additionally drive the Python engine adapter and the TS adapter; **all three must
agree.** The reference impl is illustrative — it is not the engine, and divergence between it and the
engine is itself a finding.

## Invocation

```
python research/spec/conformance/reference_runner.py            # validate vectors vs reference impl
python research/spec/conformance/reference_runner.py --adapter research.engine.conformance:FUNCTIONS
```
Exit code 0 = all pass; non-zero = at least one failure (CI-friendly).
