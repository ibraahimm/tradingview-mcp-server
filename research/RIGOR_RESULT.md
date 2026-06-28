# Rigor Pass — Result (2026-06-28)

## UPDATE — W1/W2/W3 jointly (deflated by n_trials = 12). W2 & W3 show a real signal; W1 does not.

*Data provenance: vintage **2026-06-28** (manifest `ingest/manifests/tadawul_2026-06-28.json`;
951,419 rows / 291 securities / 2001-12-31→2026-06-25; fingerprint `60cbf970…`). Run from the
vintage-backed Parquet `research/panel/tadawul_2026-06-28.parquet` — reproduced bit-for-bit.*

```
rule config       H    raw   indep  mean_xs%   t      p     p_deflated
W1  default       20  36060  3608    +0.18  +1.36  0.174    1.000
W1  default       60  36060  1906    +0.47  +1.43  0.153    1.000
W1  default      120  36060  1371    +0.23  +0.42  0.673    1.000
W1  ext60 OFF     60  44135  2033    +0.49  +1.47  0.142    1.000     (A/B delta vs gate-on: -0.02 pp)
W2  default       20  18051  2208    +0.62  +3.79  0.000    0.002  ***  <- survives deflation
W2  default       60  18051  1262    +0.88  +2.23  0.026    0.312
W2  default      120  18051   892    +1.47  +2.10  0.036    0.431
W3  default       20  10758  1580    +0.62  +2.86  0.004    0.051   .
W3  default       60  10758   892    +1.16  +2.32  0.020    0.244
W3  default      120  10758   631    +2.57  +3.01  0.003    0.031  *   <- survives deflation
```

**Walk-forward (60d market-neutral excess) — sign stability is the real test:**
```
period      W1            W2            W3
<=2010   -1.41 (t-1.0)  +2.71 (t1.5)  +1.50 (t0.5,n20)
<=2015   +1.39 (t2.2)   +0.74 (t1.0)  +0.75 (t1.0)
<=2020   +1.10 (t2.1)   +1.48 (t2.2)  +0.03 (t0.0)
<=2026   -0.53 (t-0.9)  +0.43 (t0.6)  +1.74 (t2.2)
```

- **W1 — no edge (confirmed):** every deflated p ≈ 1.0; walk-forward **flips sign** (+/-); ext60_max A/B
  = -0.02 pp (inert). The original `ext60_max` question is closed: noise.
- **W2 (second wave / continuation) — a real, positive, deflation-surviving signal at short horizon:**
  +0.62% excess @ 20d, **p_deflated = 0.002**, and **positive in all four walk-forward windows** (no
  sign flip). The most robust result in the project.
- **W3 (mature re-coil) — positive, deflation-surviving at long horizon (120d, p_deflated = 0.031),**
  positive across walk-forward, but **recency-concentrated** (driven by 2020-2026, t2.2; flat 2015-2020)
  -> more fragile than W2.

**Why this is plausible, not just data-mining:** it matches the theses — *deep-correction* (W1) names
mean-revert / show no edge, while *continuation* (W2) and *mature-trend* (W3) setups do carry positive
forward excess. And the walk-forward sign-consistency (esp. W2) is the signature data-mining usually fails.

**Caveats before calling it tradeable (the same discipline that killed ext60_max applies here):**
1. **No transaction costs.** W2 @ 20d gross excess +0.62%; Saudi round-trip (~0.155% commission + spread)
   could halve it. W3 @ 120d (+2.57%) has more cushion.
2. **t-stats are optimistic** — dedup removes within-name autocorrelation, but signals cluster in time
   (cross-sectional correlation) which inflates t. A block-bootstrap / cluster-robust SE is the honest
   next test; expect the effective significance to weaken.
3. **Multiple testing across the whole project** is larger than the 12 deflated here — W2 @ 20d
   (p_defl 0.002) has margin to survive that; W3 @ 120d (0.031) likely would not.
4. Equal-weight benchmark; one market; one vintage.

**Honest standing:** W2 (short-horizon continuation) is a **promising, deflation-surviving, walk-forward-
consistent** excess-return signal — the first real positive in the project — pending cost modelling and
cluster-robust inference. W3 is suggestive but fragile. W1 is dead.

---

## ROBUSTNESS — net-of-cost + cluster-robust (block bootstrap). Only W3 @120d survives everything.

Block bootstrap by month (B=5000, preserves same-date cross-sectional + temporal correlation, so the
i.i.d. t-stat's optimism is removed), round-trip cost = 31 bps (Saudi regulated commission both sides):

```
rule  H    n   gross%  net%  boot_p   95% CI (gross)   net>0 @95%?
W2   20  2208  +0.62  +0.31  0.002  [+0.24, +1.00]      no
W2   60  1262  +0.88  +0.57  0.048  [+0.01, +1.76]      no
W2  120   892  +1.47  +1.16  0.050  [+0.01, +2.94]      no
W3   20  1580  +0.62  +0.31  0.008  [+0.17, +1.09]      no
W3   60   892  +1.16  +0.85  0.016  [+0.22, +2.17]      no
W3  120   631  +2.57  +2.26  0.003  [+0.84, +4.32]     YES
W1  20..120                  0.18-0.69  CI spans 0       no   (dead, as before)
```

- **W2 (continuation): real but NOT tradeable.** The gross excess survives the cluster-robust bootstrap
  (boot p 0.002 at 20d, CI excludes 0) — so it is a genuine market-neutral pattern, *not* a t-stat
  artifact. But it is **too small to survive 31 bps of cost**: net 95% CI includes 0 at every horizon.
- **W3 (mature re-coil) @120d: survives the FULL gauntlet.** market-neutral ✓, deflated (p_defl 0.031) ✓,
  cluster-robust block bootstrap (p 0.003) ✓, **and net of costs** — net mean **+2.26%**, net 95% CI
  ≈ [+0.53%, +4.01%] **excludes zero**. It is a low-turnover, ~6-month-hold signal, which is exactly why
  a single round-trip cost barely dents a +2.57% move. (Even at 50 bps it stays net-positive.)
- **W1: dead at every horizon** gross and net — the `ext60_max` thesis is conclusively noise.

### Bottom line of the whole project
From a hindsight finding that was **noise** (`ext60_max`, n=15) to a properly-validated edge candidate:
**W3 @120d is the single configuration that passes market-neutralization, multiple-testing deflation,
cluster-robust inference, *and* transaction costs.** The platform did its job — it killed the false
positives (W1, and W2 once costs were charged) and let one real candidate through.

**Still required before trading W3 @120d** (do not over-read a single survivor):
1. 120-day **walk-forward** stability (the 60d walk-forward was recency-concentrated — confirm it holds pre-2020).
2. Genuine **out-of-sample** confirmation on a future vintage (paper-track it forward).
3. Capacity/liquidity at the names W3 selects; sensitivity to the cost assumption.

---

## (Original W1-only section follows)


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
