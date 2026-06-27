# Depth Probe — pre-2006 individual Tadawul equity history?

**Single question:** can we obtain daily history for **individual** Tadawul equities back to **2006 or
earlier** from any free / trial / public / practically-accessible source? (Depth only — quality,
survivorship, CAs, identifiers, licensing deferred.) Tested empirically from this environment on 2026-06-27.

## Answer

**No free/public source was empirically confirmed to reach 2006 for individual equities.** The deepest
**verified** free individual-equity history is **Yahoo Finance = 2010-03** — four years short. Every
source that *claims* pre-2006 is either **paid** (EODHD, enterprise) or **not headlessly accessible**
to verify (Investing.com/Argaam behind Cloudflare/JS, Kaggle behind auth).

## Ranking by CONFIRMED depth (I fetched real data and checked earliest dates)

| Rank | Source | Confirmed earliest (individual equities) | Reaches 2006? | Evidence |
|---|---|---|---|---|
| 1 | **Yahoo Finance** | **2010-03** (oldest bar 2010-02-01; 85/164 names start exactly 2010-03-01) | ❌ no | 164-name census, monthly non-truncating query |
| 2 | GitHub `RazanAlsallumi/Saudi_Stock_Exchange` | **2020-03-08 → 2020-04-23** only (6-week snapshot) | ❌ no | fetched the CSV; 6,992 rows, 200 names, all 2020 |
| — | **Stooq** | unobtainable | ? | curl + WebFetch both hit a JavaScript anti-bot challenge — no data |
| — | **Investing.com** | unobtainable headlessly | ? (claim) | curl → Cloudflare **403**; WebFetch shows only the default recent window; earliest needs a JS date-picker |
| — | **Argaam** (Saudi-native) | unobtainable headlessly | ? (claim) | WebFetch shows current data + an "All" chart link; no earliest date quotable without the JS chart endpoint |

Note: Yahoo's **TASI _index_** (`^TASI.SR`) is confirmed back to **1998-10-19**, but **no individual
stock** is — a direct pre-2000 daily probe returns HTTP 400 for SABIC/Al-Rajhi/STC.

## CLAIMS of pre-2006 (NOT verified here — separated deliberately)

| Source | Claim | Why unverified | Cost |
|---|---|---|---|
| **EODHD** | non-US daily from **2000-01-03** (would reach 2006) | needs an API key/trial (not testable headlessly without signup) | paid/trial |
| **Investing.com / Argaam** | multi-year Saudi history (an "All" view exists) | Cloudflare/JS — needs a browser-rendered fetch | free, but not headless |
| **Kaggle** `salwaalzahrani/...` | "collected from the official Tadawul website" | Kaggle download needs auth | free + auth |
| **LSEG / Bloomberg / Refinitiv** | decades of global history | enterprise, not accessible here | paid |

## Practical conclusion (depth only)

- **From a no-cost, headless path: 2006 is not reachable.** Confirmed free depth stops at **2010** (Yahoo).
- The **cheapest credible route to 2006** is to verify **EODHD's explicit "2000-01-03" claim on a free
  trial/API key** — a single, decisive, low-cost test (EODHD is the only practically-accessible candidate
  that *claims* the depth and can be put through our acceptance harness).
- The free-but-blocked sources (Investing.com, Argaam) would need a **JS/browser-capable fetch** (this
  sandbox has none) to confirm; even then, Saudi equity history on those typically begins ~2007–2008, so
  2006 is uncertain.

**Recommended next empirical step (still minimal cost):** obtain an EODHD trial key and pull a few old
Saudi names (SABIC 2010, Al-Rajhi 1120) for 2004–2007 — if data exists pre-2006, EODHD is the path; if
not, no realistically-accessible source reaches 2006 and we accept ~2010 free depth or a paid feed.
