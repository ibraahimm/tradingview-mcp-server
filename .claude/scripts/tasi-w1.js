#!/usr/bin/env node
/**
 * Persistent computed-filter + report renderer for the /tasi-w1 slash command.
 *
 * Strategy: Saudi Main Market (TADAWUL) names that suffered a DEEP multi-year
 * correction (anchored to the all-time high, NOT to a fixed 5-year point) and whose
 * FIRST recovery wave is underway but not yet overheated.
 *
 * The slash command does only the live MCP fetch; ALL exclusions, computed metrics,
 * thresholds, and table/summary formatting live here so they are not rebuilt each run.
 *
 * Two stages:
 *   1) filter  — input: raw screen_stocks JSON ({ total_count, stocks:[...] }).
 *                Drops 9xxx (Nomu) + REIT/Fund/ETF/Sukuk, computes the depth & wave
 *                metrics, applies all thresholds, emits { params, ..., matches, skipped }.
 *   2) report  — input: the stage-1 filter JSON (--filtered). Prints ONE box-drawing grid
 *                + summary to stdout, then a "===CHART_LINKS===" sentinel followed by a
 *                markdown "Open chart" list (printed OUTSIDE the code block by the command),
 *                and writes the full untruncated CSV (default .claude/outputs/tasi-w1.csv).
 *
 * Computed metrics (percent unless noted):
 *   DDmax    = (ATH - price_52_week_low)/ATH * 100   // peak->trough correction depth
 *   belowATH = (ATH - close)/ATH * 100               // how far still below the peak
 *   offLow   = (close/price_52_week_low - 1) * 100    // rebound off the 52-week low
 *   nrHi     = close/price_52_week_high * 100         // position vs the 52-week high
 *   ATHx     = ATH / price_52_week_high               // >~3 => peak is old/far (e.g. 2006 bubble)
 *
 * Parameters (all optional; percents given as percents, e.g. p3y_max=130 means 130%):
 *   dd_min (50)  below_min (40)  below_max (100)  offlow (30)  offlow_max (80)
 *   p3m_min (5)  p3m_max (40)  p6m_min (-10)  p6m_max (50)  p3y_max (130)
 *   value (0 = no liquidity floor, SAR)  nrhi_min (0 = descriptor only, %)
 * The Perf.* bounds are normally enforced server-side too; the script re-verifies them
 * locally so the result is correct regardless of how the screen was built.
 *
 * Usage:
 *   node tasi-w1.js stage=filter input=screen.json [p3y_max=20 offlow=25 ...]
 *   node tasi-w1.js stage=report filtered=filtered.json [csv=path maxwidth=N]
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
  dd_min: num("dd_min", 50),
  below_min: num("below_min", 40),
  below_max: num("below_max", 100), // raised 95->100 (2026-06-30): admit the most-corrected names
  offlow: num("offlow", 30),        // 35->30 (2026-07-03, D-2026-07-03-02); was 20->35 (2026-07-01)
  offlow_max: num("offlow_max", 80), // 60->80 (2026-07-01, formal request)
  p3m_min: num("p3m_min", 5),
  p3m_max: num("p3m_max", 40),
  p6m_min: num("p6m_min", -30),     // 0->-30 (2026-07-01, formal request): admit recent ignitions still negative on 6M
  p6m_max: num("p6m_max", 50),
  p3y_max: num("p3y_max", 100),     // 50->100 (2026-07-01, formal request)
  p5y_max: num("p5y_max", 100),     // 80->100 (2026-07-01, formal request)
  p10y_max: num("p10y_max", 250),
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
const chartUrl = (sym) => `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(sym)}`; // %3A: a raw ":" breaks terminal link parsers
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

  // Pass 1: main-market candidates that pass exclusions, have all required fields, and
  // satisfy the Perf bounds (re-verified locally even though the server enforces them).
  const cand = [];
  for (const s of stocks) {
    const code = String(s.symbol).split(":")[1] || "";
    if (code.startsWith("9")) continue; // Nomu / parallel market / ETFs
    if (REIT_RE.test(s.description || "")) continue; // REITs survive server type filter

    const close = s.close;
    const ath = s.all_time_high;
    const hi = s.price_52_week_high;
    const lo = s.price_52_week_low;
    const p3m = s["Perf.3M"];
    const p6m = s["Perf.6M"];
    const p3y = s["Perf.3Y"];
    const p5y = s["Perf.5Y"];
    const fbt = s.first_bar_time; // epoch seconds of the first price bar (≈ listing date)
    const avgVol = s.average_volume_30d_calc;
    const ema21 = s.EMA21; // descriptor only (tracker)
    const ema60 = s.EMA60; // tracker descriptor (ext60); extension cap removed 2026-06-30
    const ema200 = s.EMA200; // descriptor only (tracker FAILED rule).

    if ([close, ath, hi, lo, p3m, p6m, p3y].some((v) => v == null)) {
      skipped.push({ symbol: s.symbol, description: s.description });
      continue;
    }
    // listing-age requirement (DIRECT, via first_bar_time): the first traded bar must be
    // at least `min_years` old. This is exact — unlike Perf.5Y, which TradingView returns
    // even for <5y listings (e.g. recent IPOs). Younger listings are excluded by design.
    if (fbt == null) continue;
    const ageYears = (Date.now() / 1000 - fbt) / 31557600; // seconds per 365.25-day year
    if (ageYears < params.min_years) continue;
    // momentum band (re-verify; normally enforced server-side)
    if (p3m < params.p3m_min || p3m >= params.p3m_max) continue;
    if (p6m <= params.p6m_min || p6m >= params.p6m_max) continue;
    if (p3y >= params.p3y_max) continue;
    if (p5y != null && p5y >= params.p5y_max) continue; // 5Y ceiling: drop already-large recoveries (when present)
    const p10y = s["Perf.10Y"];
    if (p10y != null && p10y >= params.p10y_max) continue; // 10Y ceiling (when present; null = <10y history, allowed)

    cand.push({
      symbol: s.symbol,
      description: s.description,
      close,
      DDmax: ((ath - lo) / ath) * 100,
      belowATH: ((ath - close) / ath) * 100,
      offLow: (close / lo - 1) * 100,
      nrHi: (close / hi) * 100,
      athRatio: ath / hi,
      avgVal: avgVol != null ? avgVol * close : null,
      tag: p3y <= 0 ? "★" : "⚠up", // ★ genuine recent correction; ⚠up uptrend-leaning
      sector: s.sector || "—",
      market_cap_basic: s.market_cap_basic,
      // EMA-derived (same fields/formulae as /tasi-w2). ext60/ema21gap/emaComp/vs200 are tracker
      // descriptors only (the ext60 extension cap was removed 2026-06-30). None are shown in the table/CSV.
      ema21gap: ema21 != null ? (close / ema21 - 1) * 100 : null, // 21g
      emaComp: ema21 != null && ema60 != null ? (ema21 / ema60 - 1) * 100 : null, // cmp
      ext60: ema60 != null ? (close / ema60 - 1) * 100 : null, // x60 — tracker descriptor (no longer gated)
      vs200: ema200 != null ? (close / ema200 - 1) * 100 : null, // v200 (drives the tracker FAILED rule)
      "Perf.3M": p3m,
      "Perf.6M": p6m,
      "Perf.Y": s["Perf.Y"],
      "Perf.3Y": p3y,
      "Perf.5Y": s["Perf.5Y"],
      "Perf.10Y": s["Perf.10Y"],
    });
  }

  // Pass 2: progressive local gates — recorded as a funnel.
  const afterDD = cand.filter((r) => r.DDmax >= params.dd_min);
  const afterBelow = afterDD.filter((r) => r.belowATH >= params.below_min && r.belowATH <= params.below_max);
  const afterOff = afterBelow.filter((r) => r.offLow >= params.offlow && r.offLow < params.offlow_max);
  // NOTE: the ext60 extension cap was REMOVED 2026-06-30 (it cut as many early winners as knives;
  // ext60 is still computed as a tracker descriptor, but no longer gates entry).
  const matches = afterOff.filter(
    (r) => (params.nrhi_min <= 0 || r.nrHi >= params.nrhi_min) && (params.value <= 0 || (r.avgVal != null && r.avgVal >= params.value)),
  );
  matches.sort((a, b) => b.offLow - a.offLow);

  const funnel = {
    server: cand.length, // main-market + fields + Perf bounds
    afterDD: afterDD.length,
    afterBelow: afterBelow.length,
    afterOff: afterOff.length,
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
  "Perf 3M", "Perf 6M", "Perf 1Y", "Perf 3Y", "Perf 5Y", "Perf 10Y",
  "ATH/52WHigh", "Avg Traded Value", "Mkt Cap", "Sector", "Tag",
];
const SHORT = ["Sym", "Name", "DD%", "bATH", "offL", "nrHi", "3M", "6M", "1Y", "3Y", "5Y", "10Y", "ATHx", "Val", "Cap", "Sec", "Tag"];
const ALIGN = ["l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "l", "l"];
const NAME_MAX = 22;
const SEC_MAX = 13;

function stageReport() {
  if (!args.filtered) throw new Error("stage=report requires filtered=<filter.json|->");
  const filtered = readJson(args.filtered);
  const p = filtered.params || params;
  const csvPath = args.csv || ".claude/outputs/tasi-w1.csv";
  const rows = filtered.matches || [];

  // CSV: full, untruncated values
  const csvRows = rows.map((r) => [
    r.symbol, r.description, r.DDmax.toFixed(1), r.belowATH.toFixed(1), r.offLow.toFixed(1), r.nrHi.toFixed(1),
    r["Perf.3M"]?.toFixed(1) ?? "—", r["Perf.6M"]?.toFixed(1) ?? "—", r["Perf.Y"]?.toFixed(1) ?? "—",
    r["Perf.3Y"]?.toFixed(1) ?? "—", r["Perf.5Y"]?.toFixed(1) ?? "—", r["Perf.10Y"]?.toFixed(1) ?? "—",
    r.athRatio?.toFixed(2) ?? "—", "SAR " + compact(r.avgVal), "SAR " + compact(capSar(r.market_cap_basic)), r.sector, r.tag,
  ]);
  const csv = "﻿" + [HEADERS, ...csvRows].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
  mkdirSync(dirname(csvPath), { recursive: true });
  writeFileSync(csvPath, csv);

  // grid: compact values
  const gridRows = rows.map((r) => [
    r.symbol.replace(/^TADAWUL:/, ""), trunc(r.description, NAME_MAX),
    r0(r.DDmax), r0(r.belowATH), r0(r.offLow), r0(r.nrHi),
    r0(r["Perf.3M"]), r0(r["Perf.6M"]), r0(r["Perf.Y"]), r0(r["Perf.3Y"]), r0(r["Perf.5Y"]), r0(r["Perf.10Y"]),
    r1(r.athRatio), valM(r.avgVal), capc(capSar(r.market_cap_basic)), trunc(r.sector || "—", SEC_MAX), r.tag,
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
    `  1. after base conditions (≥${p.min_years}y since listing, Perf.3M/6M/3Y/5Y + scope) : ${fn.server ?? "—"}`,
    `  2. after DDmax ≥ ${p.dd_min}%                       : ${fn.afterDD ?? "—"}`,
    `  3. after belowATH ∈ [${p.below_min},${p.below_max}]%        : ${fn.afterBelow ?? "—"}`,
    `  4. after offLow ≥ ${p.offlow}%                       : ${fn.afterOff ?? "—"}`,
    `  5. final survivors                                 : ${fn.final ?? rows.length}`,
    "",
    grid.text,
    "",
  ];
  if (rows.length === 0) out.push("No matches.");
  out.push(`Matches: ${rows.length} of ${filtered.total_count} server-screened TADAWUL stocks.`);
  if (rows.length) {
    const top = rows.slice(0, 3).map((r) => `${r.description} (${r.symbol.split(":")[1]}, off-low +${Math.round(r.offLow)}%)`);
    out.push(`Strongest 3 (by rebound off 52W low): ${top.join("; ")}.`);
    const corr = rows.filter((r) => r["Perf.3Y"] <= 0).length;
    out.push(`Quality split: ${corr} genuine recent corrections (Perf.3Y ≤ 0); ${rows.length - corr} uptrend-leaning (Perf.3Y > 0 — loosen p3y_max to purge).`);
    const oldPeak = rows.filter((r) => r.athRatio >= 3).map((r) => r.symbol.split(":")[1]);
    if (oldPeak.length) out.push(`Old/far peak flag (ATHx ≥ 3, likely pre-2006-bubble anchor): ${oldPeak.join(", ")}.`);
  }
  out.push(
    `Filters: ≥${p.min_years}y since listing (first_bar_time), DDmax ≥ ${p.dd_min}%, belowATH ∈ [${p.below_min},${p.below_max}]%, offLow ∈ [${p.offlow},${p.offlow_max})%, ` +
      `Perf.3M ∈ [${p.p3m_min},${p.p3m_max})%, Perf.6M ∈ (${p.p6m_min},${p.p6m_max})%, Perf.3Y < ${p.p3y_max}%, Perf.5Y < ${p.p5y_max}%, Perf.10Y < ${p.p10y_max}%` +
      (p.value > 0 ? `, value ≥ SAR ${compact(p.value)}` : ", value floor OFF") +
      (p.nrhi_min > 0 ? `, nrHi ≥ ${p.nrhi_min}%` : "") + ".",
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
    rows.forEach((r) =>
      out.push(`${r.symbol.split(":")[1]} ${trunc(r.description, 34)}: [open chart](${chartUrl(r.symbol)})`),
    );
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
  process.stderr.write("tasi-w1.js error: " + err.message + "\n");
  process.exit(1);
}
