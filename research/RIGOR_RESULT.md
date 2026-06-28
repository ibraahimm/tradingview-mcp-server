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

## CONDITIONAL REGIME TEST — W1 is market-TIMING (beta), W2 is SELECTION but only in NORMAL regimes

The rigor/robust passes conditioned only on each *name's* deep correction and pooled across all
regimes. This tests the original W1 thesis directly: *does the edge live in market-wide crisis /
deep-drawdown environments, and is it stock-**selection** skill or market-**timing**/recovery (beta)?*
Pre-registered regimes (declared before testing, no threshold fishing): market drawdown from a
**trailing-1y high** (not ATH — the 2006 bubble would otherwise mark a decade as "drawdown") at
**dd≥20%** and **dd≥35%**, plus **below-EMA200**; "normal" = dd<20%. Two readings: **B = absolute**
forward return (includes the market bounce → timing/beta), **A = selection** = market-neutral excess
(name minus same-date cohort → removes the bounce). Cluster-robust block bootstrap. `mkt%` = the
market's own forward return (the beta benchmark). Driver: `research/regime_run.py`.

Regime coverage (6,326 market days): dd≥20% 23%, dd≥35% 11%, below200 38%, normal 77% — crises are a
genuine minority (validates the rolling-drawdown choice; an ATH measure would have been ~always-on).

```
W1                                            W2
regime    H    n   B abs(p)  mkt   A sel(p)   |  n    B abs(p)  mkt   A sel(p)
dd>=20%  20  358  +1.22(.32) +2.0  -0.81(.20) | 82  +0.85(.51) +2.1  -1.26(.28)
dd>=20%  60  218  +1.70(.59) +3.0  -1.31(.18) | 57  +3.75(.28) +4.8  -1.11(.58)
dd>=20% 120  165  +5.95(.05) +8.2  -2.00(.30) | 35  +7.64(.13) +8.2  -0.63(.82)
dd>=35%  20   69  +6.81(.01) +9.4  -2.51(.21) |  4  [n=4 — degenerate, ignore]
dd>=35%  60   57  +8.07(.02)+11.6  -3.54(.07) |  3  [n=3 — degenerate, ignore]
normal   20 3250  +0.55(.33) +0.2  +0.29(.07) |2126 +1.54(.00)*+0.8  +0.69(.00)*
normal   60 1688  +1.40(.26) +0.7  +0.70(.06) |1205 +2.40(.01)*+1.4  +0.98(.03)*
normal  120 1206  +2.69(.08) +2.1  +0.54(.45) | 857 +3.96(.01)*+2.5  +1.55(.03)*
```

### W1 — market-TIMING / recovery exposure, NOT selection (and slightly negative selection in crises)
- In the deepest crises (**dd≥35%**) W1 names post large **absolute** returns (+6.8%/+8.1%, p<0.05) —
  but the **market itself returned more** (mkt +9.4%/+11.6%), and **selection is negative** (−2.5/−3.5):
  W1 names *underperform their own peers* during crises. The big absolute number is **pure market
  bounce (beta)**, not skill. Verdict: **TIMING/recovery**.
- Leave-one-crisis-out (dd≥20%): the weak positive **absolute** collapses when **2008** is removed
  (60d +1.70→−0.45) — it is 2008/beta-driven. **Selection stays negative across every leave-out** (a
  stable non-edge). The dd≥35% timing is necessarily concentrated in the one or two episodes deep
  enough to qualify.
- **Answer to the original W1 hypothesis:** "deep-correction names bought in a market crisis outperform
  as it recovers" is true **only in the trivial beta sense** — you would have done as well or better
  holding the index. **No stock-selection alpha; if anything negative.** The unconditional "no edge" was
  not masking a hidden conditional selection edge.

### W2 — stock-SELECTION skill, but in NORMAL regimes, not crises
- W2's edge is significant and consistent **only in the `normal` regime**: selection **A +0.69/+0.98/
  +1.55%** (p .00/.03/.03) at 20/60/120d, and absolute **B > mkt** (it beats beta too). This *locates*
  the real W2 signal found in the robust pass — it is a **continuation/coil setup that needs a
  functioning uptrend**, exactly what crises remove.
- In crisis regimes W2 shows **no selection edge** (point estimates negative; dd≥35% n=3–4 is degenerate
  — the p=0.000 there is a tiny-sample artifact, **not** evidence). Crisis buckets are also underpowered,
  but there is no hint of hidden crisis alpha.
- Verdict: **SELECTION, normal-regime only.**

### Bottom line
- **W1 = TIMING/beta**, not selection — the crisis thesis holds only as market exposure (and is
  2008-concentrated). It is *not* a stock picker.
- **W2 = SELECTION**, and counter-intuitively in **normal** markets, not the deep-drawdown environment.
- *Caveat:* crisis cells are small/underpowered and the dd≥35% buckets lean on the 1–2 deepest episodes;
  read the W1 timing result as "beta, mostly 2008", not a precise estimate.

---

## SEQUENTIAL LIFECYCLE TEST — the lifecycle is REAL as a classifier; W2 is the tradeable value-add; W3 is a success MARKER, not an entry

Evaluates the waves as ONE pipeline (collapse → W1 entry → W2 confirmation → W3 normal trend), measuring
the *incremental* value of each stage rather than each wave standalone. Pre-registered: link window
**K=504 td (~2y)** max gap between consecutive stages; horizons **[20,60,120,252,504]** (the lifecycle is
multi-year); cluster-robust block bootstrap; stage-improvement = **P(mean_later > mean_earlier)**. Two
views: **TRADEABLE** (enter at each stage's own trigger, prior stage required in the *past* — look-ahead
free) and **DIAGNOSTIC** (split W1 entries by whether they *later* progress — uses the future on purpose,
to test the lifecycle as a classifier). Driver: `research/lifecycle_run.py`.

Funnel (raw triggers): W1 36,060 → W1→W2 (linked) 16,250 → W1→W2→W3 (linked) 5,594.

### TRADEABLE — enter at the stage trigger (abs%, selection%, step-up P vs previous stage)
```
   H  stage         n     abs%(p)   sel%(p)   step-up P(abs>prev)
  20  W1          3608  +0.62(.25) +0.18(.28)
  20  W1->W2      1956  +1.59(.00) +0.65(.00)   P=0.93   <- W2 improves W1 (abs AND selection)
  20  W1->W2->W3   820  +1.04(.08) +0.10(.70)   P=0.21   <- W3 entry is WORSE than W2
 120  W1          1371  +3.08(.03) +0.23(.69)
 120  W1->W2       782  +4.48(.00) +1.45(.06)   P=0.77   <- W2 still improves W1
 120  W1->W2->W3   320  +2.78(.24) +1.24(.24)   P=0.26   <- W3 entry worse
 252  W1           919 +12.22(.00) +2.20(.11)
 252  W1->W2       526  +7.68(.00) +1.38(.35)   P=0.13   <- at long H, entering LATER captures less
 504  W1           599 +18.82(.00) +2.82(.18)
 504  W1->W2       366  +8.66(.01) -0.42(.85)   P=0.03
 504  W1->W2->W3   156  -1.00(.81) +1.86(.70)   P=0.07   <- W3 entry: the run is already spent
```
- **W1→W2 genuinely improves on W1 at trading horizons (≤120d)** — higher absolute (step-up P 0.77–0.93)
  *and* selection turns significant (20d +0.65, p.00). This cross-confirms the regime finding (W2 = real
  selection). **W2 is the value-add stage.**
- **W3 as a third sequential ENTRY adds nothing — it subtracts** (step-up P 0.21–0.26 at ≤120d; negative
  at 504d). By the time W3 confirms you are buying a spent move.
- At long horizons the *earlier* entry (W1) shows the biggest absolute — it captures the whole recovery —
  but that is largely beta (selection insignificant), consistent with W1 = timing/beta.

### DIAGNOSTIC — do W1 entries that LATER progress separate winners from failures? (uses future)
```
   H  W1 group       n     abs%(p)   hit%     conf-W2 vs fail
 120  fail-W2      567  -4.32(.03)   31%
 120  conf-W2 all  865  +6.75(.00)   57%     P=1.00, d=+11.1pp
 120  conf-W3      451  +9.80(.00)   63%
 252  fail-W2      407  -0.60(.87)   32%
 252  conf-W3      315 +25.32(.00)   73%     (conf-W2 all: P=1.00, d=+17.0pp)
 504  fail-W2      292  +0.42(.97)   32%
 504  conf-W3      214 +42.20(.00)   80%     (conf-W2 all: P=1.00, d=+22.3pp)
```
- **Decisive.** W1 entries that NEVER confirm W2 earn **−4.3% (120d), 31% hit** — the failed recoveries /
  falling knives. Those that confirm earn **+6.8%, 57% hit (P=1.00 better)**. Those that reach W3 earn
  **+9.8 / +25.3 / +42.2%** with hit-rate climbing **63→73→80%**. The lifecycle progression is an
  extremely powerful EX-POST classifier of recovery success — exactly the design thesis.

### Synthesis — what the lifecycle test actually proves
1. **The lifecycle is REAL.** Progression W1→W2→W3 cleanly tracks recovery quality (diagnostic: monotone,
   huge separation, P=1.00). Hypothesis #2 ("W2 removes failed recoveries, keeps successes") is confirmed.
2. **W2 is the tradeable refinement** — it both filters the −4% failure cohort *and* improves the entry
   (better absolute + real selection) at ≤120d. W1→W2 is the methodology's genuine progressive step.
3. **W3 does NOT refine as an entry — it MARKS completion.** Reaching W3 is the strongest success signal
   (great for *classification / monitoring / exit*), but entering at the W3 trigger buys an exhausted run.
   This is the central failure point: the information W3 carries is real, but the value is already priced.

### Failure points (inputs to the disciplined Phase-2 search)
- **F1 — W3 is mis-cast as an entry.** Its forward upside is spent; it belongs as a hold/exit/monitor
  state, or its gates (Perf.3Y≥50 etc.) mechanically pick already-run names.
- **F2 — the prize is EX-ANTE progression.** The diagnostic separates winners from failures only *with
  hindsight*. A feature that predicts, AT W1/W2 ENTRY, which names will progress to W3 would convert the
  classifier into a tradeable edge.
- **F3 — the −4% fail-W2 cohort** (falling knives that never confirm) is the costliest error; flagging it
  at W1 entry (skip / size-down) is high value.

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
