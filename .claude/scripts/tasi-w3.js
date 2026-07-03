#!/usr/bin/env node
/**
 * Persistent computed-filter + report renderer for the /tasi-w3 slash command.
 *
 * Strategy: Saudi Main Market (TADAWUL) names ONE leg beyond /tasi-w2 — a MATURE uptrend
 * that already ran its TASI-W1 (first turn off the deep low) and TASI-W2 (first coil + advance), has
 * climbed back to / near (or made) new highs, and is now forming the NEXT contraction (a fresh
 * EMA coil higher up) that sets up the following leg. Unlike TASI-W1/TASI-W2 this is NOT a "deeply
 * corrected" screen — DDmax/belowATH/offLow are descriptors here, not gates. The structure is:
 *   mature trend (close > EMA200) + the coil again (EMA21≈EMA60, reclaim EMA21) +
 *   a pull-back from a recent high (nrHi band) + a genuine multi-year advance (Perf.3Y/5Y mins).
 *
 * The slash command does only the live MCP fetch; ALL exclusions, computed metrics, thresholds,
 * and table/summary formatting live here so they are not rebuilt each run.
 *
 * Two stages:
 *   1) filter  — input: raw screen_stocks JSON ({ total_count, stocks:[...] }).
 *   2) report  — input: stage-1 filter JSON; prints box-grid + summary, a "===CHART_LINKS===\"
 *                sentinel, then a markdown link list; writes CSV (default .claude/outputs/tasi-w3.csv).
 *
 * Computed metrics (percent unless noted):
 *   DDmax/belowATH/offLow/nrHi  — as in wave2 (here DDmax/belowATH/offLow are DESCRIPTORS)
 *   ema21gap = (close/EMA21-1)*100   emaComp = (EMA21/EMA60-1)*100   // the coil
 *   ext60 = (close/EMA60-1)*100      vs200 = (close/EMA200-1)*100    // trend / maturity
 *
 * TASI-W3 gate logic (all defaults below):
 *   mature trend     : close > EMA60 AND vs200 > vs200_min (close > EMA200)
 *   the coil again   : emaComp in [ema_gap_min, ema_gap_max],  close >= EMA21 AND ema21gap <= ext21_max
 *   pulled back high : nrHi in [nrhi_min, nrhi_max]   (eased off a recent high — the post-TASI-W2-peak contraction)
 *   genuine winner   : Perf.3Y in [p3y_min, p3y_max), Perf.5Y in [p5y_min, p5y_max)  (multi-year advance)
 *   not overheated   : Perf.1M in (p1m_min,p1m_max), Perf.3M in [p3m_min,p3m_max), Perf.6M in (p6m_min,p6m_max),
 *                      Perf.1Y in (py_min,py_max), Perf.10Y < p10y_max
 *
 * Parameters (all optional; percents as percents):
 *   ema_gap_min(-2) ema_gap_max(5) ext21_max(10) vs200_min(0) nrhi_min(78) nrhi_max(98)
 *   p1m_min(0) p1m_max(15) p3m_min(0) p3m_max(40) p6m_min(0) p6m_max(100) py_min(0) py_max(200)
 *   p3y_min(50) p3y_max(300) p5y_min(30) p5y_max(500) p10y_max(1000) min_years(5) value(0)
 *
 * Usage:
 *   node tasi-w3.js stage=filter input=screen.json [p3y_min=80 ...]
 *   node tasi-w3.js stage=report filtered=filtered.json [csv=path maxwidth=N]
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
  // structure / coil gates
  ema_gap_min: num("ema_gap_min", -2),
  ema_gap_max: num("ema_gap_max", 5),
  ext21_max: num("ext21_max", 10),
  vs200_min: num("vs200_min", 0),
  nrhi_min: num("nrhi_min", 78),
  nrhi_max: num("nrhi_max", 98),
  // perf ladder (mins + maxes)
  p1m_min: num("p1m_min", 0),
  p1m_max: num("p1m_max", 15),
  p3m_min: num("p3m_min", 0),
  p3m_max: num("p3m_max", 40),
  p6m_min: num("p6m_min", 0),
  p6m_max: num("p6m_max", 100),
  py_min: num("py_min", 0),
  py_max: num("py_max", 200),
  p3y_min: num("p3y_min", 50),
  p3y_max: num("p3y_max", 300),
  p5y_min: num("p5y_min", 30),
  p5y_max: num("p5y_max", 500),
  p10y_max: num("p10y_max", 1000),
  // misc
  min_years: num("min_years", 5),
  value: num("value", 0),
};

function readJson(spec) {
  const raw = spec === "-" ? readFileSync(0, "utf8") : readFileSync(spec, "utf8");
  return JSON.parse(raw);
}

// ---------- formatting helpers ----------
const REIT_RE = /REIT|Fund|ETF|Sukuk/i;
const LINKS_SENTINEL = "===CHART_LINKS===";
const chartUrl = (sym) => `https://www.tradingview.com/chart/?symbol=${sym}`;
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
const r0 = (x) => (x == null || Number.isNaN(x) ? "—" : String(Math.round(x)));
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
    const p5y = s["Perf.5Y"];
    const fbt = s.first_bar_time;
    const avgVol = s.average_volume_30d_calc;

    if ([close, ath, hi, lo, ema21, ema60, ema200, p1m, p3m, p6m, pY, p3y, p5y].some((v) => v == null)) {
      skipped.push({ symbol: s.symbol, description: s.description });
      continue;
    }
    if (fbt == null) continue;
    const ageYears = (Date.now() / 1000 - fbt) / 31557600;
    if (ageYears < params.min_years) continue;
    // Perf ladder (re-verify; normally enforced server-side). MINS ensure a genuine multi-year advance.
    if (p1m <= params.p1m_min || p1m >= params.p1m_max) continue;
    if (p3m < params.p3m_min || p3m >= params.p3m_max) continue;
    if (p6m <= params.p6m_min || p6m >= params.p6m_max) continue;
    if (pY <= params.py_min || pY >= params.py_max) continue;
    if (p3y < params.p3y_min || p3y >= params.p3y_max) continue; // floor = the TASI-W3 discriminator
    if (p5y < params.p5y_min || p5y >= params.p5y_max) continue;
    const p10y = s["Perf.10Y"];
    if (p10y != null && p10y >= params.p10y_max) continue; // null = <10y history, allowed

    cand.push({
      symbol: s.symbol,
      description: s.description,
      close,
      DDmax: ((ath - lo) / ath) * 100, // descriptor
      belowATH: ((ath - close) / ath) * 100, // descriptor (≈0 ⇒ at/near new highs)
      offLow: (close / lo - 1) * 100, // descriptor
      nrHi: (close / hi) * 100,
      ema21gap: (close / ema21 - 1) * 100,
      emaComp: (ema21 / ema60 - 1) * 100,
      ext60: (close / ema60 - 1) * 100,
      vs200: (close / ema200 - 1) * 100,
      athRatio: ath / hi,
      avgVal: avgVol != null ? avgVol * close : null,
      tag: ((ath - close) / ath) * 100 < 10 ? "★" : "↑", // ★ = at/near new highs; ↑ = still climbing toward ATH
      sector: s.sector || "—",
      market_cap_basic: s.market_cap_basic,
      "Perf.1M": p1m,
      "Perf.3M": p3m,
      "Perf.6M": p6m,
      "Perf.Y": pY,
      "Perf.3Y": p3y,
      "Perf.5Y": p5y,
      "Perf.10Y": s["Perf.10Y"],
    });
  }

  // Progressive local gates — funnel.
  const afterTrend = cand.filter((r) => r.ext60 > 0); // close > EMA60
  const afterAbove200 = afterTrend.filter((r) => r.vs200 > params.vs200_min); // close > EMA200 (mature)
  const afterCoil = afterAbove200.filter(
    (r) =>
      r.ema21gap >= 0 &&
      r.ema21gap <= params.ext21_max &&
      r.emaComp >= params.ema_gap_min &&
      r.emaComp <= params.ema_gap_max,
  );
  const matches = afterCoil.filter(
    (r) =>
      r.nrHi >= params.nrhi_min && r.nrHi <= params.nrhi_max && (params.value <= 0 || (r.avgVal != null && r.avgVal >= params.value)),
  );
  matches.sort((a, b) => a.ext60 - b.ext60); // tightest to EMA60 support first

  const funnel = {
    base: cand.length,
    afterTrend: afterTrend.length,
    afterAbove200: afterAbove200.length,
    afterCoil: afterCoil.length,
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
  "1M", "3M", "6M", "1Y", "3Y", "5Y", "Cap", "Sec", "Tag",
];
const ALIGN = ["l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "l", "l"];
const NAME_MAX = 22;
const SEC_MAX = 13;

function stageReport() {
  if (!args.filtered) throw new Error("stage=report requires filtered=<filter.json|->");
  const filtered = readJson(args.filtered);
  const p = filtered.params || params;
  const csvPath = args.csv || ".claude/outputs/tasi-w3.csv";
  const rows = filtered.matches || [];

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

  const gridRows = rows.map((r) => [
    r.symbol.replace(/^TADAWUL:/, ""), trunc(r.description, NAME_MAX),
    r0(r.DDmax), r0(r.belowATH), r0(r.offLow), r0(r.nrHi),
    r1(r.ema21gap), r1(r.emaComp), r1(r.ext60), r0(r.vs200),
    r0(r["Perf.1M"]), r0(r["Perf.3M"]), r0(r["Perf.6M"]), r0(r["Perf.Y"]), r0(r["Perf.3Y"]), r0(r["Perf.5Y"]),
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

  const fn = filtered.funnel || {};
  const out = [
    "Funnel (Saudi Main Market, after 9xxx/REIT exclusion):",
    `  1. base conditions (≥${p.min_years}y listing, Perf ladder incl 3Y≥${p.p3y_min} 5Y≥${p.p5y_min} + scope) : ${fn.base ?? "—"}`,
    `  2. after trend close > EMA60                  : ${fn.afterTrend ?? "—"}`,
    `  3. after mature trend close > EMA200          : ${fn.afterAbove200 ?? "—"}`,
    `  4. after coil EMA21/EMA60 ∈ [${p.ema_gap_min},${p.ema_gap_max}]% + reclaim : ${fn.afterCoil ?? "—"}`,
    `  5. after nrHi ∈ [${p.nrhi_min},${p.nrhi_max}]% (pulled back from high) = survivors : ${fn.final ?? rows.length}`,
    "",
    grid.text,
    "",
  ];
  if (rows.length === 0) out.push("No matches.");
  out.push(`Matches: ${rows.length} of ${filtered.total_count} server-screened TADAWUL stocks.`);
  if (rows.length) {
    const top = rows.slice(0, 3).map((r) => `${r.description} (${r.symbol.split(":")[1]}, +${r.ext60.toFixed(1)}% vs EMA60)`);
    out.push(`Tightest 3 (nearest EMA60 support): ${top.join("; ")}.`);
    const atHi = rows.filter((r) => r.belowATH < 10).length;
    out.push(`ATH proximity: ${atHi} at/near new highs (belowATH < 10%, ★); ${rows.length - atHi} still climbing toward ATH (↑).`);
  }
  out.push(
    `Filters: ≥${p.min_years}y listing, close > EMA60, close > EMA200 (vs200 > ${p.vs200_min}), ` +
      `EMA21/EMA60 ∈ [${p.ema_gap_min},${p.ema_gap_max}]%, close ∈ [EMA21, +${p.ext21_max}%], nrHi ∈ [${p.nrhi_min},${p.nrhi_max}]%, ` +
      `Perf.1M ∈ (${p.p1m_min},${p.p1m_max})%, Perf.3M ∈ [${p.p3m_min},${p.p3m_max})%, Perf.6M ∈ (${p.p6m_min},${p.p6m_max})%, ` +
      `Perf.1Y ∈ (${p.py_min},${p.py_max})%, Perf.3Y ∈ [${p.p3y_min},${p.p3y_max})%, Perf.5Y ∈ [${p.p5y_min},${p.p5y_max})%, Perf.10Y < ${p.p10y_max}%` +
      (p.value > 0 ? `, value ≥ SAR ${compact(p.value)}` : ", value floor OFF") +
      ". DDmax/belowATH/offLow are descriptors (not gated).",
  );
  const skipped = filtered.skipped || [];
  out.push(`Missing-data warnings: ${skipped.length ? skipped.map((s) => `${s.symbol}`).join(", ") + "." : "none."}`);
  out.push("Scope: Saudi Main Market (TADAWUL) only — Nomu/parallel-market (9xxx), ETFs, and REITs/funds excluded.");
  out.push(`CSV: ${csvPath}`);

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
  process.stderr.write("tasi-w3.js error: " + err.message + "\n");
  process.exit(1);
}
