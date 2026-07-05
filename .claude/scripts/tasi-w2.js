#!/usr/bin/env node
/**
 * Persistent computed-filter + report renderer for the /tasi-w2 slash command.
 *
 * Strategy: Saudi Main Market (TADAWUL) names that keep the /tasi-w1 deep-correction
 * DNA (still well below the all-time high) but are one leg further along — the FIRST wave
 * already advanced and HELD, the stock pulled back into a tight EMA compression, reclaimed
 * its short-term EMA, and is resuming. This is the SECOND-wave / continuation entry:
 * strength-after-rest, not a falling knife.
 *
 * The slash command does only the live MCP fetch; ALL exclusions, computed metrics,
 * thresholds, and table/summary formatting live here so they are not rebuilt each run.
 *
 * Two stages:
 *   1) filter  — input: raw screen_stocks JSON ({ total_count, stocks:[...] }).
 *                Drops 9xxx (Nomu) + REIT/Fund/ETF/Sukuk, computes the depth/EMA metrics,
 *                applies all thresholds, emits { params, ..., matches, skipped }.
 *   2) report  — input: the stage-1 filter JSON (--filtered). Prints ONE box-drawing grid
 *                + summary to stdout, then a "===CHART_LINKS===" sentinel followed by a
 *                markdown "Open chart" list (printed OUTSIDE the code block by the command),
 *                and writes the full untruncated CSV (default .claude/outputs/tasi-w2.csv).
 *
 * Computed metrics (percent unless noted):
 *   DDmax     = (ATH - price_52_week_low)/ATH * 100   // peak->trough correction depth
 *   belowATH  = (ATH - close)/ATH * 100               // how far still below the peak
 *   offLow    = (close/price_52_week_low - 1) * 100    // rebound off the 52-week low
 *   nrHi      = close/price_52_week_high * 100         // position vs the 52-week high (descriptor)
 *   ema21gap  = (close/EMA21 - 1) * 100                // close vs short-term EMA (reclaim/extension)
 *   emaComp   = (EMA21/EMA60 - 1) * 100                // EMA compression: fast vs mid EMA (the coil)
 *   ext60     = (close/EMA60 - 1) * 100                // extension above the mid (trend) EMA
 *   vs200     = (close/EMA200 - 1) * 100               // close vs the long EMA (descriptor / tag)
 *   ATHx      = ATH / price_52_week_high               // >~3 => peak is old/far (e.g. 2006 bubble)
 *
 * Wave-2 gate logic (all defaults below):
 *   deep-correction context : DDmax >= dd_min,  belowATH in [below_min, below_max],
 *                             offLow in [offlow, offlow_max)
 *   Stage-2 trend           : close > EMA60                       (EMA200 is a descriptor, NOT a gate —
 *                             a name recovering from a deep drop often still has EMA60 < a falling EMA200)
 *   pullback / resumption   : close >= EMA21   (reclaimed; the 10% extension cap was REMOVED 2026-06-30)
 *                             emaComp in [ema_gap_min, ema_gap_max]      (fast EMA coiled near the mid EMA)
 *   guardrails (D-2026-07-04-01): Perf.1M < p1m_max (not overly extended),
 *                             Perf.1Y > py_min (no severe 1Y weakness); p1m lower band stays removed
 *   recency / not-overheated: Perf.3M in [p3m_min, p3m_max), Perf.6M in (p6m_min, p6m_max),
 *                             Perf.3Y < p3y_max, Perf.5Y < p5y_max, Perf.10Y < p10y_max
 *
 * Parameters (all optional; percents given as percents):
 *   dd_min (45)  below_min (20)  below_max (95)  offlow (30)  offlow_max (80)
 *   ema_gap_min (-2)  ema_gap_max (5)
 *   p1m_max (30)  p3m_min (0)  p3m_max (40)  p6m_min (-10)  p6m_max (80)
 *   py_min (-40)  p3y_max (130)  p5y_max (200)  p10y_max (400)
 *   min_years (5)  value (0 = no liquidity floor, SAR)  nrhi_min (0 = descriptor only, %)
 * The Perf.* bounds are normally enforced server-side too; the script re-verifies them
 * locally so the result is correct regardless of how the screen was built.
 *
 * Usage:
 *   node tasi-w2.js stage=filter input=screen.json [offlow=40 ema_gap_max=8 ...]
 *   node tasi-w2.js stage=report filtered=filtered.json [csv=path maxwidth=N]
 * Input paths accept "-" for stdin.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

// ---------- arg parsing (key=value tokens) ----------
const args = {};
for (const tok of process.argv.slice(2)) {
  const eq = tok.indexOf("=");
  if (eq === -1) continue;
  args[tok.slice(0, eq)] = tok.slice(eq + 1);
}
const num = (k, def) => (args[k] !== undefined ? Number(args[k]) : def);

const params = {
  dd_min: num("dd_min", 45),
  below_min: num("below_min", 20),
  below_max: num("below_max", 95),  // 80->95 (2026-07-04, D-2026-07-04-02)
  offlow: num("offlow", 30),         // 35->30 (2026-07-03, D-2026-07-03-02); was 30->35 (2026-07-01)
  offlow_max: num("offlow_max", 80), // 100->80 (2026-07-01, formal request)
  ema_gap_min: num("ema_gap_min", -2),
  ema_gap_max: num("ema_gap_max", 5),
  p1m_max: num("p1m_max", 30),       // guardrail: Perf.1M ceiling (D-2026-07-04-01); 20->30 (D-2026-07-05-01)
  p3m_min: num("p3m_min", 0),
  p3m_max: num("p3m_max", 40),
  p6m_min: num("p6m_min", -10),      // 3->-10 (2026-07-01, formal request)
  p6m_max: num("p6m_max", 80),
  py_min: num("py_min", -40),        // guardrail: Perf.1Y floor (D-2026-07-04-01); -20->-40 (D-2026-07-05-01)
  p3y_max: num("p3y_max", 130),      // 100->130 (2026-07-01, formal request)
  p5y_max: num("p5y_max", 200),
  p10y_max: num("p10y_max", 400),
  min_years: num("min_years", 5),
  value: num("value", 0),
  nrhi_min: num("nrhi_min", 0),
};

function readJson(spec) {
  const raw = spec === "-" ? readFileSync(0, "utf8") : readFileSync(spec, "utf8");
  return JSON.parse(raw);
}

// ---------- formatting helpers ----------
const REIT_RE = /REIT|Fund|ETF|Sukuk/i;
const LINKS_SENTINEL = "===CHART_LINKS===";
// Percent-encode the ":" (TADAWUL%3A2340): terminal link matchers truncate the URL at a
// raw colon in the query (the app then gets symbol=TADAWUL -> "symbol doesn't exist"),
// while the app decodes %3A and opens the chart correctly (verified 2026-07-04).
const chartUrl = (sym) => `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(sym)}`;
// TradingView returns market_cap_basic in USD (fundamental_currency_code = "USD"), while all
// prices are in SAR. SAR is pegged to USD at 3.75, so convert market cap to SAR for consistency.
const SAR_PER_USD = 3.75;
const capSar = (usd) => (usd == null ? null : usd * SAR_PER_USD);

function compact(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toFixed(0);
}
function capc(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (a >= 1e6) return Math.round(n / 1e6) + "M";
  if (a >= 1e3) return Math.round(n / 1e3) + "K";
  return String(Math.round(n));
}
const r0 = (x) => (x == null || Number.isNaN(x) ? "—" : String(Math.round(x))); // integer
const r1 = (x) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(1));
const valM = (n) => (n == null || Number.isNaN(n) ? "—" : Math.round(n / 1e6) + "M");
function trunc(s, max) {
  s = String(s);
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}
function csvCell(s) {
  s = String(s);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

// Render a continuous box-drawing grid.
function renderGrid(headers, rows, aligns) {
  const w = headers.map((h, i) => Math.max(h.length, ...rows.map((r) => r[i].length)));
  const seg = (ch) => w.map((width) => ch.repeat(width + 2));
  const top = "┌" + seg("─").join("┬") + "┐";
  const mid = "├" + seg("─").join("┼") + "┤";
  const bot = "└" + seg("─").join("┴") + "┘";
  const fmtRow = (cells) =>
    "│" +
    cells
      .map((c, i) => {
        const pad = " ".repeat(w[i] - c.length);
        return " " + (aligns[i] === "r" ? pad + c : c + pad) + " ";
      })
      .join("│") +
    "│";
  return { text: [top, fmtRow(headers), mid, ...rows.map(fmtRow), bot].join("\n"), width: top.length };
}

// ---------- stage: filter ----------
function stageFilter() {
  if (!args.input) throw new Error("stage=filter requires input=<screen.json|->");
  const data = readJson(args.input);
  const stocks = data.stocks || [];
  const skipped = [];

  // Pass 1: main-market candidates that pass exclusions, have all required fields, satisfy the
  // listing-age rule, and satisfy the Perf bounds (re-verified locally even though the server
  // enforces them). The EMA/structure ratios are computed here and gated progressively below.
  const cand = [];
  for (const s of stocks) {
    const code = String(s.symbol).split(":")[1] || "";
    if (code.startsWith("9")) continue; // Nomu / parallel market / ETFs
    if (REIT_RE.test(s.description || "")) continue; // REITs survive server type filter

    const close = s.close;
    const ath = s.all_time_high;
    const hi = s.price_52_week_high;
    const lo = s.price_52_week_low;
    const ema21 = s.EMA21;
    const ema60 = s.EMA60;
    const ema200 = s.EMA200;
    const p1m = s["Perf.1M"];
    const p3m = s["Perf.3M"];
    const p6m = s["Perf.6M"];
    const pY = s["Perf.Y"];
    const p3y = s["Perf.3Y"];
    const fbt = s.first_bar_time; // epoch seconds of the first price bar (≈ listing date)
    const avgVol = s.average_volume_30d_calc;

    if ([close, ath, hi, lo, ema21, ema60, ema200, p1m, p3m, p6m, pY, p3y].some((v) => v == null)) {
      skipped.push({ symbol: s.symbol, description: s.description });
      continue;
    }
    // listing-age requirement (DIRECT, via first_bar_time): the first traded bar must be at
    // least `min_years` old. Exact — unlike Perf.5Y, which TradingView returns even for <5y listings.
    if (fbt == null) continue;
    const ageYears = (Date.now() / 1000 - fbt) / 31557600; // seconds per 365.25-day year
    if (ageYears < params.min_years) continue;
    // Perf bounds (re-verify; normally enforced server-side)
    if (p3m < params.p3m_min || p3m >= params.p3m_max) continue;
    if (p6m <= params.p6m_min || p6m >= params.p6m_max) continue;
    if (p1m >= params.p1m_max) continue; // guardrail: not overly extended short-term (D-2026-07-04-01)
    if (pY <= params.py_min) continue; // guardrail: no severe 1Y weakness (D-2026-07-04-01)
    if (p3y >= params.p3y_max) continue;
    const p5y = s["Perf.5Y"];
    if (p5y != null && p5y >= params.p5y_max) continue;
    const p10y = s["Perf.10Y"];
    if (p10y != null && p10y >= params.p10y_max) continue; // null = <10y history, allowed

    cand.push({
      symbol: s.symbol,
      description: s.description,
      close,
      DDmax: ((ath - lo) / ath) * 100,
      belowATH: ((ath - close) / ath) * 100,
      offLow: (close / lo - 1) * 100,
      nrHi: (close / hi) * 100,
      ema21gap: (close / ema21 - 1) * 100,
      emaComp: (ema21 / ema60 - 1) * 100,
      ext60: (close / ema60 - 1) * 100,
      vs200: (close / ema200 - 1) * 100,
      athRatio: ath / hi,
      avgVal: avgVol != null ? avgVol * close : null,
      tag: close > ema200 ? "★" : "⚠e", // ★ = also above EMA200 (full Stage-2); ⚠e = early (long trend still down)
      sector: s.sector || "—",
      market_cap_basic: s.market_cap_basic,
      "Perf.1M": p1m,
      "Perf.3M": p3m,
      "Perf.6M": p6m,
      "Perf.Y": pY,
      "Perf.3Y": p3y,
      "Perf.5Y": s["Perf.5Y"],
      "Perf.10Y": s["Perf.10Y"],
    });
  }

  // Pass 2: progressive local gates — recorded as a funnel.
  const afterDD = cand.filter((r) => r.DDmax >= params.dd_min);
  const afterBelow = afterDD.filter((r) => r.belowATH >= params.below_min && r.belowATH <= params.below_max);
  const afterOff = afterBelow.filter((r) => r.offLow >= params.offlow && r.offLow < params.offlow_max);
  const afterTrend = afterOff.filter((r) => r.ext60 > 0); // close > EMA60
  const afterPull = afterTrend.filter(
    (r) =>
      r.ema21gap >= 0 && // close >= EMA21 (reclaimed) — 10% extension cap REMOVED 2026-06-30
      r.emaComp >= params.ema_gap_min &&
      r.emaComp <= params.ema_gap_max, // fast EMA coiled near the mid EMA
  );
  const matches = afterPull.filter(
    (r) => (params.nrhi_min <= 0 || r.nrHi >= params.nrhi_min) && (params.value <= 0 || (r.avgVal != null && r.avgVal >= params.value)),
  );
  matches.sort((a, b) => a.ext60 - b.ext60); // tightest setups first (nearest EMA60 support)

  const funnel = {
    base: cand.length, // main-market + fields + age + Perf bounds
    afterDD: afterDD.length,
    afterBelow: afterBelow.length,
    afterOff: afterOff.length,
    afterTrend: afterTrend.length,
    final: matches.length,
  };

  process.stdout.write(
    JSON.stringify(
      { params, total_count: data.total_count ?? stocks.length, screened_count: stocks.length, funnel, matches, skipped },
      null,
      2,
    ) + "\n",
  );
}

// ---------- stage: report ----------
const HEADERS = [
  "Symbol", "Company", "DDmax %", "Below ATH %", "Off 52W Low %", "vs 52W High %",
  "Close/EMA21 %", "EMA21/EMA60 %", "Close/EMA60 %", "Close/EMA200 %",
  "Perf 1M", "Perf 3M", "Perf 6M", "Perf 1Y", "Perf 3Y", "Perf 5Y", "Perf 10Y",
  "ATH/52WHigh", "Avg Traded Value", "Mkt Cap", "Sector", "Tag",
];
const SHORT = [
  "Sym", "Name", "DD%", "bATH", "offL", "nrHi", "21g", "cmp", "x60", "v200",
  "1M", "3M", "6M", "1Y", "3Y", "Cap", "Sec", "Tag",
];
const ALIGN = ["l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "l", "l"];
const NAME_MAX = 22;
const SEC_MAX = 13;

function stageReport() {
  if (!args.filtered) throw new Error("stage=report requires filtered=<filter.json|->");
  const filtered = readJson(args.filtered);
  const p = filtered.params || params;
  const csvPath = args.csv || ".claude/outputs/tasi-w2.csv";
  const rows = filtered.matches || [];

  // CSV: full, untruncated values
  const csvRows = rows.map((r) => [
    r.symbol, r.description, r.DDmax.toFixed(1), r.belowATH.toFixed(1), r.offLow.toFixed(1), r.nrHi.toFixed(1),
    r.ema21gap.toFixed(2), r.emaComp.toFixed(2), r.ext60.toFixed(2), r.vs200.toFixed(2),
    r["Perf.1M"]?.toFixed(1) ?? "—", r["Perf.3M"]?.toFixed(1) ?? "—", r["Perf.6M"]?.toFixed(1) ?? "—",
    r["Perf.Y"]?.toFixed(1) ?? "—", r["Perf.3Y"]?.toFixed(1) ?? "—", r["Perf.5Y"]?.toFixed(1) ?? "—", r["Perf.10Y"]?.toFixed(1) ?? "—",
    r.athRatio?.toFixed(2) ?? "—", "SAR " + compact(r.avgVal), "SAR " + compact(capSar(r.market_cap_basic)), r.sector, r.tag,
  ]);
  const csv = "﻿" + [HEADERS, ...csvRows].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
  mkdirSync(dirname(csvPath), { recursive: true });
  writeFileSync(csvPath, csv);

  // grid: compact values
  const gridRows = rows.map((r) => [
    r.symbol.replace(/^TADAWUL:/, ""), trunc(r.description, NAME_MAX),
    r0(r.DDmax), r0(r.belowATH), r0(r.offLow), r0(r.nrHi),
    r1(r.ema21gap), r1(r.emaComp), r1(r.ext60), r0(r.vs200),
    r0(r["Perf.1M"]), r0(r["Perf.3M"]), r0(r["Perf.6M"]), r0(r["Perf.Y"]), r0(r["Perf.3Y"]),
    capc(capSar(r.market_cap_basic)), trunc(r.sector || "—", SEC_MAX), r.tag,
  ]);
  const grid = renderGrid(SHORT, gridRows, ALIGN);

  const maxWidth = args.maxwidth ? Number(args.maxwidth) : 0;
  if (maxWidth > 0 && grid.width > maxWidth) {
    process.stdout.write(
      `WIDTH PROBLEM: the drawn grid is ${grid.width} columns wide, exceeding maxwidth=${maxWidth}. ` +
        `Not printing a broken table.\nFull results are in the CSV: ${csvPath}\n`,
    );
    return;
  }

  // Funnel block (printed at the very top, inside the code block).
  const fn = filtered.funnel || {};
  const out = [
    "Funnel (Saudi Main Market, after 9xxx/REIT exclusion):",
    `  1. base conditions (≥${p.min_years}y listing, Perf.1M<${p.p1m_max}, Perf.1Y>${p.py_min} + 3M/6M/3Y/5Y/10Y + scope) : ${fn.base ?? "—"}`,
    `  2. after DDmax ≥ ${p.dd_min}%                          : ${fn.afterDD ?? "—"}`,
    `  3. after belowATH ∈ [${p.below_min},${p.below_max}]%                 : ${fn.afterBelow ?? "—"}`,
    `  4. after offLow ∈ [${p.offlow},${p.offlow_max})%                : ${fn.afterOff ?? "—"}`,
    `  5. after trend close > EMA60                  : ${fn.afterTrend ?? "—"}`,
    `  6. after EMA21 reclaim (close ≥ EMA21, EMA21/EMA60 ∈ [${p.ema_gap_min},${p.ema_gap_max}]%) = survivors : ${fn.final ?? rows.length}`,
    "",
    grid.text,
    "",
  ];
  if (rows.length === 0) out.push("No matches.");
  out.push(`Matches: ${rows.length} of ${filtered.total_count} server-screened TADAWUL stocks.`);
  if (rows.length) {
    const top = rows.slice(0, 3).map((r) => `${r.description} (${r.symbol.split(":")[1]}, +${r.ext60.toFixed(1)}% vs EMA60)`);
    out.push(`Tightest 3 (nearest EMA60 support): ${top.join("; ")}.`);
    const aligned = rows.filter((r) => r.vs200 > 0).length;
    out.push(`Trend alignment: ${aligned} fully aligned (close > EMA200, ★); ${rows.length - aligned} early (still below EMA200, ⚠e — long downtrend not yet up).`);
    const oldPeak = rows.filter((r) => r.athRatio >= 3).map((r) => r.symbol.split(":")[1]);
    if (oldPeak.length) out.push(`Old/far peak (ATHx ≥ 3, deep drawdown vs an old high — confirm on long-term chart): ${oldPeak.join(", ")}.`);
  }
  out.push(
    `Filters: ≥${p.min_years}y listing (first_bar_time), DDmax ≥ ${p.dd_min}%, belowATH ∈ [${p.below_min},${p.below_max}]%, offLow ∈ [${p.offlow},${p.offlow_max})%, ` +
      `close > EMA60, close ≥ EMA21, EMA21/EMA60 ∈ [${p.ema_gap_min},${p.ema_gap_max}]%, ` +
      `Perf.1M < ${p.p1m_max}%, Perf.3M ∈ [${p.p3m_min},${p.p3m_max})%, Perf.6M ∈ (${p.p6m_min},${p.p6m_max})%, ` +
      `Perf.1Y > ${p.py_min}%, Perf.3Y < ${p.p3y_max}%, Perf.5Y < ${p.p5y_max}%, Perf.10Y < ${p.p10y_max}%` +
      (p.value > 0 ? `, value ≥ SAR ${compact(p.value)}` : ", value floor OFF") +
      (p.nrhi_min > 0 ? `, nrHi ≥ ${p.nrhi_min}%` : ", nrHi descriptor") + ".",
  );
  const skipped = filtered.skipped || [];
  out.push(`Missing-data warnings: ${skipped.length ? skipped.map((s) => `${s.symbol}`).join(", ") + "." : "none."}`);
  out.push("Scope: Saudi Main Market (TADAWUL) only — Nomu/parallel-market (9xxx), ETFs, and REITs/funds excluded.");
  out.push(`CSV: ${csvPath}`);

  // chart links (printed OUTSIDE the code block by the command)
  out.push(LINKS_SENTINEL);
  if (rows.length) {
    out.push("**Open chart (click a symbol):**");
    out.push("");
    rows.forEach((r) => out.push(`${r.symbol.split(":")[1]} ${trunc(r.description, 34)}: [open chart](${chartUrl(r.symbol)})`));
  } else {
    out.push("_No matches — no chart links._");
  }

  process.stdout.write(out.join("\n") + "\n");
}

// ---------- dispatch ----------
const stage = args.stage || "filter";
try {
  if (stage === "filter") stageFilter();
  else if (stage === "report") stageReport();
  else throw new Error(`unknown stage='${stage}' (expected filter|report)`);
} catch (err) {
  process.stderr.write("tasi-w2.js error: " + err.message + "\n");
  process.exit(1);
}
