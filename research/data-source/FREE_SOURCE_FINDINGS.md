# Free / Trial Source Findings — empirical test (2026-06-27)

Goal: find the **strongest practical, least-cost** data path before assuming a paid vendor. I tested
what is **actually reachable from this environment** (curl/HTTP, no signup), normalized the one usable
source into the acceptance-harness format, and ran it through the **same MUST gates** as any vendor.

**Headline:** **no reachable free source is survivorship-free.** The one freely-usable source (Yahoo
Finance) is **empirically REJECTED by the acceptance harness on all five MUST gates** — most decisively,
it **404s on delisted Saudi names** and its equity history begins **~2010, not 2006**.

## What I actually tested (confirmed = I fetched it; not assumption)

| Source | Reachable? | Evidence |
|---|---|---|
| **Yahoo Finance** chart API (`query1.finance.yahoo.com`, no key) | ✅ **yes** | 200 OK; real daily SAR data fetched + normalized + run through the harness |
| **Stooq** CSV (`stooq.com/q/d/l`) | ❌ blocked | returns a JavaScript anti-bot challenge, not data (unusable headless) |
| **stockanalysis.com** API | ❌ error | HTTP 400 on `.SR` symbols |
| **Twelve Data** free tier | ⚠️ not usable free | needs an API key; free/Basic plan excludes **deep international history** (paid) — per docs |
| **GitHub/Kaggle community datasets** | ⚠️ weak | small/static (e.g. "9 banks", macro 2027-row sets); Kaggle needs auth; current-names-only |

## Yahoo Finance — characterized against the MUSTs (empirical)

Real fetch of `2222/1120/2010/4280.SR` (+ delisted `1040/1090.SR`), normalized via
`acceptance/normalizers/yahoo_normalize.py`, then `run_acceptance.py`:

```
R1 MUST FAIL  delisted=0 (1040.SR & 1090.SR -> HTTP 404), earliest=2010-03-03 (<=2006: False)
R2 MUST FAIL  adjusted close bundles dividends+splits; not cleanly split-vs-unadjusted reconcilable
R3 MUST FAIL  1616 reconciliation mismatches (adjClose is div+split adjusted, not split-only)
R4 MUST FAIL  no stable identifier / ticker-change history (id == ticker)
R6 MUST FAIL  no delisted securities present
R5 PARTIAL PASS  calendar correct: Sun–Thu trading week confirmed (no Fri/Sat bars)
RESULT: REJECT — MUST failures: R1, R2, R3, R4, R6
```

| Dimension | Yahoo finding (confirmed) |
|---|---|
| **History depth** | Equities from **~2010-03** (SABIC/Al-Rajhi/Kingdom all start 2010-03-03); Aramco from its 2019 IPO; **TASI index back to 1998**. **Not 2006 for stocks.** |
| **Current vs delisted** | **Current only.** Delisted names (`1040.SR` Alawwal, `1090.SR`) return **HTTP 404** — survivorship-biased. |
| **Adjusted vs unadjusted** | Both available: **raw OHLC** + **adjClose**. But adjClose is **dividend+split adjusted** (total-return-style), so it does **not** give a clean split-only price-return series. |
| **Corporate actions** | Split + dividend **events** present (ratios + amounts with ex-dates) — usable to rebuild split-only adjustment with effort. |
| **Symbol continuity** | None — keyed on the reusable `.SR` ticker; no stable surrogate, no ticker-change history. |
| **Calendar** | **Correct** — Sun–Thu trading week confirmed empirically (256 daily bars in 2015; no Fri/Sat). |
| **API access** | Practical: no key, JSON, but `range=max&interval=1d` **downsamples** (~monthly); true daily needs **bounded `period1/period2` windows** (chunk by year). Bot-tolerant. |

## Conclusion (explicit, as requested)

**No free/trial source reachable here satisfies the survivorship-free requirement (R1).** This is not a
gap in one provider — it is inherent to free retail data: these feeds track the **live** universe and
drop delisted names, and their Saudi depth starts ~2010. Free sources therefore **cannot** support a
survivorship-free, corporate-action-aware Tadawul backtest on their own.

The acceptance harness earned its keep: it converted "Yahoo might work" into an objective, reproducible
**REJECT on real data**.

## Best practical fallback (least cost, evidence-based)

A two-track path — start free *now*, pay only what's needed to de-bias:

1. **Now, zero cost — run the pipeline on real (biased) data.** Use Yahoo to build a **survivors-only,
   ~2010-onward** panel and run `build_panel → screen → event_study → governance` end-to-end. This gives
   the **first real (if biased) result** immediately and de-risks the engine on live data — **clearly
   labelled "survivorship-biased, post-2010, indicative only"** (the governance layer's whole point is
   to stop us trusting it further than that).
2. **De-bias incrementally (still low cost):** hand-curate the **delisted set + pre-2010** from Tadawul
   announcements (the market is small) into the production `reference/` — this is the survivorship work
   that no free feed will do for us, and it is the same curation the architecture already requires.
3. **Close R1 properly with a *cheap* trial — now justified, not assumed.** The empirical result shows
   free **cannot** meet R1, so a low-cost vendor trial (EODHD / SAHMK) is the rational next spend —
   decided objectively by running their trial sample through this same harness. We are not assuming we
   must pay; we have **evidence** that the free tier stops at survivorship + 2006.

**Recommended immediate step:** build the Yahoo ingestion path (track 1) to produce the first real
indicative numbers at zero cost, **in parallel** with curating the delisted/pre-2010 reference (track 2).
Reach for a paid trial only to remove the survivorship bias the harness has now demonstrated.

## Sources

- Yahoo chart API (tested directly): `https://query1.finance.yahoo.com/v8/finance/chart/2222.SR`
- Twelve Data pricing/coverage (free excludes deep intl history): https://twelvedata.com/pricing , https://support.twelvedata.com/en/articles/5214728-getting-historical-data
- Community datasets: https://github.com/Hussain-Alsalman/tasi , https://github.com/RazanAlsallumi/Saudi_Stock_Exchange , https://www.kaggle.com/datasets/salwaalzahrani/saudi-stock-exchange-tadawul
- Saudi Exchange market data (official EOD = last 5 years, listed-only): https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/market-services/market-information-services/market-data
