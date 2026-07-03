# Forward-return evidence — TASI-W2 momentum-gate removal + offlow_min 35→30

**Dated Report** (point-in-time; never updated — see `/DOCUMENTATION.md`). Written 2026-07-03.
**Comparability coordinate of these runs:** (`spec_version 1.0.0`, latest Methodology entry in
force **D-2026-07-01-02**) — i.e. computed against the pre-change canon.
**Panel:** `tadawul_2026-06-28.parquet` (951,419 rows / 291 securities, fingerprint per manifest).
**Method:** full-history event study; non-overlapping (dedup) signals; market-neutral excess
(signal minus same-date cross-section); net of 31 bps round-trip; block-bootstrap CI/p (B=5000);
Bonferroni-deflated. Drivers: `research/experiments/w2_momentum_gate_removal.py`,
`research/experiments/offlow30_promotion_test.py` (override-only; canon untouched by the runs).
Gate *removal* approximated by widening bounds to ±1e18 — exact for the eligible ≥5y universe
(perf_1m/perf_1y never null there).

## Run 1 — TASI-W2 with vs without the `p1m_min`/`p1m_max`/`py_min` gates

```text
spec         H     n     xs%    net%  boot_p  p_defl   95% CI (xs)      (n_trials=6)
W2 CUR      20  2080   +0.68 +0.37  +0.001  +0.005   [+0.27, +1.08]
W2 CUR      60  1174   +1.04 +0.73  +0.026  +0.156   [+0.14, +1.96]
W2 CUR     120   838   +1.31 +1.00  +0.144  +0.862   [-0.49, +3.06]
W2 NOGATE   20  3037   +0.16 -0.15  +0.430  +1.000   [-0.24, +0.55]
W2 NOGATE   60  1666   +0.24 -0.07  +0.592  +1.000   [-0.64, +1.10]
W2 NOGATE  120  1133   +0.14 -0.17  +0.876  +1.000   [-1.57, +1.80]

P(cur>nogate): 0.97 @20d (Δ+0.52pp) · 0.90 @60d (Δ+0.80pp) · 0.84 @120d (Δ+1.17pp)
```

## Run 2 — offlow_min 35→30 (W1, W2) and the full proposed W2 end-state

```text
spec        H     n     xs%    net%  boot_p  p_defl   95% CI (xs)      (n_trials=15)
W1 CUR     20  4608   +0.20 -0.11  +0.170  +1.000   [-0.08, +0.49]
W1 CUR     60  2300   +0.56 +0.25  +0.133  +1.000   [-0.17, +1.33]
W1 CUR    120  1552   +1.30 +0.99  +0.215  +1.000   [-0.59, +3.53]
W1 OL30    20  5376   +0.18 -0.13  +0.193  +1.000   [-0.09, +0.47]
W1 OL30    60  2631   +0.24 -0.07  +0.522  +1.000   [-0.55, +0.97]
W1 OL30   120  1741   +0.91 +0.60  +0.304  +1.000   [-0.71, +2.72]
W2 CUR     20  2080   +0.68 +0.37  +0.001  +0.012   [+0.27, +1.08]
W2 CUR     60  1174   +1.04 +0.73  +0.026  +0.390   [+0.14, +1.96]
W2 CUR    120   838   +1.31 +1.00  +0.144  +1.000   [-0.49, +3.06]
W2 OL30    20  2428   +0.64 +0.33  +0.001  +0.012   [+0.26, +1.02]
W2 OL30    60  1354   +0.84 +0.53  +0.046  +0.690   [+0.02, +1.70]
W2 OL30   120   949   +1.04 +0.73  +0.202  +1.000   [-0.57, +2.63]
W2 PROP    20  3593   +0.19 -0.12  +0.294  +1.000   [-0.17, +0.55]
W2 PROP    60  1915   +0.29 -0.02  +0.487  +1.000   [-0.55, +1.14]
W2 PROP   120  1282   -0.00 -0.31  +0.980  +1.000   [-1.53, +1.56]

P(cur>variant):
  W1 CUR vs W1 OL30 : 0.53 @20d · 0.73 @60d · 0.61 @120d
  W2 CUR vs W2 OL30 : 0.56 @20d · 0.62 @60d · 0.60 @120d
  W2 CUR vs W2 PROP : 0.97 @20d · 0.88 @60d · 0.87 @120d
```

## Findings

1. **The `p1m`/`py_min` gates are load-bearing for TASI-W2's historical per-signal edge.** With
   them, W2 CUR is deflated-significant at 20d and net-positive at every horizon; without them
   the excess collapses to noise and is **net-negative after cost at every horizon**
   (P(cur>nogate) 0.84–0.97). Removal admits ~46% more deduped signals of materially lower quality.
2. **`offlow_min` 35→30 alone is return-neutral-to-slightly-diluting.** W2 keeps its deflated
   20d significance (+0.64%, p_defl 0.012); ~17% more signals; mild per-signal dilution at
   60/120d (P ≈ 0.56–0.62). W1 (no cross-sectional edge to protect) shows the same recall-vs-
   quality profile (P ≈ 0.53–0.73).
3. **The combined proposed W2 end-state inherits the gate-removal damage** — indistinguishable
   from noise, net-negative at all horizons.

These are pooled 20-year results on one vintage; regime-split and true OOS were not run here.
