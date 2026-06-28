# Rigor Pass — Result (2026-06-28)

First defensible, out-of-sample evaluation of the W1 screen on **real** data (adjusted,
survivorship-inclusive Saudi Exchange, 2001–2026, 288 names incl. 20 delisted with curated
terminal values). Method: **market-neutral excess** returns (signal minus the cross-sectional date
mean), **non-overlapping** signals (one per name per holding window), **walk-forward**, **Bonferroni
deflation** (`n_trials = 2 configs × 3 horizons = 6`). Driver: `research/rigor_run.py`.

## Headline: no statistically significant, stable edge — and `ext60_max` is inert

```
config              H    raw   indep  mean_xs%    t      p     p_deflated
W1 (ext60_max=10)   20  35416  3546    +0.16   +1.22  0.222   1.000
W1 (ext60_max=10)   60  35416  1874    +0.46   +1.37  0.171   1.000
W1 (ext60_max=10)  120  35416  1349    +0.17   +0.30  0.762   1.000
W1 (ext60 OFF)      20  43372  3861    +0.22   +1.57  0.116   0.694
W1 (ext60 OFF)      60  43372  1999    +0.47   +1.37  0.171   1.000
W1 (ext60 OFF)     120  43372  1413    +0.59   +0.97  0.334   1.000
```

1. **Dedup matters enormously:** 35,416 raw daily signals → **~1,874 independent** (60d). The
   indicative "n=34,801" was ~19× autocorrelated repeats of the same setups — its tiny error bars
   were an illusion.
2. **No significant excess:** market-neutral excess is small and positive (+0.16% to +0.46% per
   independent signal) but **every t-stat is ≤ 1.6 and every deflated p-value is ≈ 1.0.** After
   honest multiple-testing correction, W1 is statistically **indistinguishable from the market**.
3. **`ext60_max` is empirically inert** — the original question, finally answered on real data:
   ```
   60d:  with ext60_max=10  mean_xs +0.46% (n=1874)   |   ext60 OFF  +0.47% (n=1999)
   delta (gate − off): −0.01 pp
   ```
   The gate discards ~8k raw signals for **a one-hundredth-of-a-point** change in excess return. It
   neither helps nor hurts. The `n=15` hindsight "finding" that started this project was noise —
   now confirmed on 20+ years of real data with proper rigor.
4. **Not stable across time (walk-forward, 60d excess):**
   ```
   ≤2010  n=106  −1.32%  (t −0.92)
   ≤2015  n=482  +1.36%  (t +2.09)
   ≤2020  n=644  +1.03%  (t +1.99)
   ≤2026  n=642  −0.50%  (t −0.80)
   ```
   The excess **flips sign** (negative early, positive mid-decade, negative recently). A robust edge
   would be consistently positive; this reverses — regime-dependent, not a durable signal.

## Verdict

On real, adjusted, survivorship-inclusive Saudi data, **W1 has no statistically significant,
stable, out-of-sample excess return**, and the **`ext60_max` ceiling adds nothing**. The earlier
"signals underperform the rest" was itself an artifact (signals cluster in down regimes; comparing
to a non-date-matched "rest" mixed time periods) — on a date-matched market-neutral basis W1 is
slightly positive but insignificant. The honest summary: *no edge demonstrated*, not *negative edge*.

This is exactly the outcome the governance layer was built to surface — it stops us calling noise an
edge, which is the mistake that began the whole project.

## Caveats (do not over-read)

- No transaction costs / liquidity / capacity yet — a portfolio sim would only **reduce** the small
  positive excess.
- Benchmark = equal-weight cross-sectional date mean (not cap- or sector-matched) — simple but reasonable.
- One rule (W1); W2/W3 not yet put through the rigor pass.
- One market (Tadawul), one data vintage.

## Next options

1. Put **W2 / W3** through the same rigor pass (do their continuation/mature-coil theses hold up?).
2. **Parameter search** for any W1 configuration with a deflation-surviving edge (expect none, but it
   closes the question).
3. **Portfolio simulation** with costs — only worthwhile if a gate first survives the rigor pass.
