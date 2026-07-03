# Forward-return evidence — TASI-W2 guardrail restoration (p1m_max=20, py_min=−20)

**Dated Report** (point-in-time; never updated). Written 2026-07-04.
**Comparability coordinate of these runs:** (`spec_version 1.0.0`, latest Methodology entry in
force **D-2026-07-03-02**) — computed against the gateless post-simplification canon.
**Panel:** `tadawul_2026-06-28.parquet` (951,419 rows / 291 securities).
**Method:** full-history event study; dedup signals; market-neutral excess; net 31 bps;
block-bootstrap CI/p (B=5000); Bonferroni (n_trials=9). Driver:
`research/experiments/w2_guardrails_restore_test.py` — the candidate is built as an in-memory
rule (current canon + the two proposed predicates); no official file was touched by the runs.

## Specs

- **W2 CUR** — current canon (post-D-2026-07-03-02: no Perf.1M/Perf.1Y gates, offlow 30).
- **W2 GUARD** — the proposal: `perf_1m lt 20` + `perf_1y gt −20` added to CUR (no p1m_min).
- **W2 OLDGATES** — context: the pre-simplification momentum gates (`perf_1m ∈ (0,15)`,
  `perf_1y > 0`) on the current base.

## Results

```text
spec           H     n     xs%    net%  boot_p  p_defl   95% CI (xs)
W2 CUR        20  3593   +0.19 -0.12  +0.294  +1.000   [-0.17, +0.55]
W2 CUR        60  1915   +0.29 -0.02  +0.487  +1.000   [-0.55, +1.14]
W2 CUR       120  1282   -0.00 -0.31  +0.980  +1.000   [-1.53, +1.56]
W2 GUARD      20  3264   +0.31 +0.00  +0.093  +0.839   [-0.06, +0.67]
W2 GUARD      60  1719   +0.53 +0.22  +0.215  +1.000   [-0.30, +1.36]
W2 GUARD     120  1153   +1.00 +0.69  +0.216  +1.000   [-0.59, +2.54]
W2 OLDGATES   20  2428   +0.64 +0.33  +0.001  +0.007   [+0.26, +1.02]
W2 OLDGATES   60  1354   +0.84 +0.53  +0.046  +0.414   [+0.02, +1.70]
W2 OLDGATES  120   949   +1.04 +0.73  +0.202  +1.000   [-0.57, +2.63]

P(variant>cur):
  W2 GUARD    : 0.68 @20d (Δ+0.12pp) · 0.65 @60d (Δ+0.24pp) · 0.81 @120d (Δ+1.00pp)
  W2 OLDGATES : 0.96 @20d (Δ+0.45pp) · 0.82 @60d (Δ+0.55pp) · 0.82 @120d (Δ+1.04pp)
```

## Findings

1. **The proposed guardrails improve on the current gateless rule at every horizon** —
   P(GUARD>CUR) 0.65–0.81, excess back to +0.31/+0.53/+1.00% and net back to
   break-even-or-positive — while dropping only ~9% of the deduped signals (3264 vs 3593 @20d).
2. **They recover part, not all, of the pre-simplification edge.** OLDGATES (the removed
   band + Perf.1Y>0) remains deflated-significant at 20d (+0.64%, p_defl 0.007) with ~25% fewer
   signals; GUARD is directionally positive but not deflated-significant (p_defl 0.839 @20d).
3. The binding tail-trims: `perf_1m < 20` removes only the most extended short-term movers;
   `perf_1y > −20` removes severe 1-year losers — together a recall-preserving quality floor.

Pooled 20-year, one vintage; no regime split or OOS here.
