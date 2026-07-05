# Forward-return evidence — TASI-W2 guardrail widening (p1m_max 20→30, py_min −20→−40)

**Dated Report** (point-in-time; never updated). Written 2026-07-05.
**Comparability coordinate of these runs:** (`spec_version 1.0.0`, latest Methodology entry in
force **D-2026-07-04-02**) — computed against the post-depth-widening canon.
**Panel:** `tadawul_2026-06-28.parquet` (951,419 rows / 291 securities).
**Method:** full-history event study; dedup signals; market-neutral excess; net 31 bps;
block-bootstrap CI/p (B=5000); Bonferroni (n_trials=12). Driver:
`research/experiments/w2_guardrails_widen_test.py` — pure `params_overrides` (both guardrail
parameters exist in canon); no official file was touched by the runs.

## Specs

- **W2 CUR** — current canon (post-D-2026-07-04-02: `perf_1m < 20`, `perf_1y > −20`).
- **W2 WIDE** — the proposal: both guardrails widened (`p1m_max=30`, `py_min=−40`).
- **W2 P1M30 / W2 PY-40** — each widening alone (attribution).

## Results

```text
spec         H     n     xs%    net%  boot_p  p_defl   95% CI (xs)
W2 CUR      20  4420   +0.21 -0.10  +0.149  +1.000   [-0.08, +0.50]
W2 CUR      60  2368   +0.41 +0.10  +0.236  +1.000   [-0.26, +1.08]
W2 CUR     120  1618   +1.12 +0.81  +0.064  +0.763   [-0.07, +2.33]
W2 WIDE     20  4903   +0.18 -0.13  +0.194  +1.000   [-0.09, +0.46]
W2 WIDE     60  2647   +0.30 -0.01  +0.375  +1.000   [-0.40, +0.99]
W2 WIDE    120  1787   +0.63 +0.32  +0.257  +1.000   [-0.43, +1.72]
W2 P1M30    20  4578   +0.19 -0.12  +0.186  +1.000   [-0.09, +0.47]
W2 P1M30    60  2469   +0.29 -0.02  +0.426  +1.000   [-0.41, +0.98]
W2 P1M30   120  1676   +0.83 +0.52  +0.166  +1.000   [-0.33, +1.99]
W2 PY-40    20  4723   +0.19 -0.12  +0.170  +1.000   [-0.08, +0.48]
W2 PY-40    60  2532   +0.43 +0.12  +0.196  +1.000   [-0.24, +1.11]
W2 PY-40   120  1726   +0.84 +0.53  +0.133  +1.000   [-0.22, +1.95]

P(variant>cur):
  W2 WIDE  : 0.43 @20d (Δ−0.03pp) · 0.42 @60d (Δ−0.11pp) · 0.28 @120d (Δ−0.49pp)
  W2 P1M30 : 0.45 @20d (Δ−0.02pp) · 0.41 @60d (Δ−0.12pp) · 0.37 @120d (Δ−0.29pp)
  W2 PY-40 : 0.45 @20d (Δ−0.02pp) · 0.52 @60d (Δ+0.01pp) · 0.37 @120d (Δ−0.28pp)
```

## Findings

1. **Recall widening with mild per-signal dilution.** The combined widening adds ~11% deduped
   signals @20d (4903 vs 4420) and is near-neutral at 20/60d (P(WIDE>CUR) 0.43/0.42,
   Δ −0.03/−0.11pp) but visibly diluting at 120d (P=0.28, Δ −0.49pp; excess +0.63% vs +1.12%).
2. **Attribution is even.** Each widening alone lands in the same near-neutral-to-mildly-diluting
   band (P 0.37–0.52); neither dominates the 120d dilution — the marginal names admitted by each
   relaxation simply carry somewhat weaker long-horizon quality than the incumbent cohort.
3. **No spec is deflated-significant** here (best p_defl 0.763, W2 CUR @120d); the marginal-name
   effect is a dilution of a non-significant base, not the removal of a proven edge — a weaker
   adverse signal than the D-2026-07-03-02 gate removal, and one class worse than the
   return-neutral D-2026-07-04-02 depth widening.

Pooled 20-year, one vintage; no regime split or OOS here.
