#!/usr/bin/env node
/**
 * Persistent computed-filter + report renderer for the /saudi-momentum slash command.
 *
 * The slash command is responsible only for the live MCP data fetches; ALL local
 * exclusions, computed filters, and table/summary formatting live here so they are
 * not rebuilt on every run.
 *
 * Two stages:
 *
 *   1) filter  — input: raw screen_stocks JSON ({ total_count, stocks: [...] }).
 *                Applies local exclusions (9xxx codes, REIT/Fund/ETF/Sukuk) and the
 *                computed conditions (gain_from_low, ema_spread, adr_pct, avg_value).
 *                Emits JSON: { params, total_count, screened_count, matches, skipped }.
 *                The command reads matches[].symbol to drive the lookup_symbols call.
 *
 *   2) report  — inputs: the stage-1 filter JSON (--filtered) plus the lookup_symbols
 *                JSON (--lookup, { symbols: [...] }). Merges them and prints ONE continuous
 *                box-drawing grid table (┌┬┐ ├┼┤ └┴┘ │ ─) + short summary to stdout, and
 *                writes the full untruncated results as CSV (default .claude/outputs/
 *                saudi-momentum.csv). This box-grid is the fixed, default report format.
 *                After the summary it emits a "===CHART_LINKS===" sentinel line followed
 *                by a markdown "Open chart" list (one clickable TradingView link per match).
 *                The command splits stdout on that line: the part before goes verbatim in a
 *                ```text code block; the part after is printed as markdown (outside the block)
 *                so the links are clickable.
 *
 * Usage:
 *   node saudi-momentum.js stage=filter input=screen.json [gain=40 ema_fast=21 ...]
 *   node saudi-momentum.js stage=report filtered=filtered.json lookup=lookup.json
 *
 * Parameters (percent values are given as percents, e.g. gain=40 means 40%):
 *   gain (40) ema_fast (21) ema_slow (60) spread (5) adr (1) value (5000000)
 *   spread_min (optional) — lower bound on ema_spread in percent. When set, the
 *     strict fast>slow check is replaced by ema_spread >= spread_min, making
 *     `spread` a two-sided band (e.g. spread_min=-4 spread=4 → ±4% around the
 *     EMA crossover). Requires the caller to drop the server-side EMA{fast}>EMA{slow}
 *     filter so near-crossover names actually reach this stage. Omit for default behavior.
 *
 * Input file paths can also be supplied on stdin instead of a file (input=- / filtered=- / lookup=-).
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
  gain: num("gain", 40),
  ema_fast: num("ema_fast", 21),
  ema_slow: num("ema_slow", 60),
  spread: num("spread", 5),
  // Optional lower bound on ema_spread (percent). When supplied, the strict
  // fast>slow "confirmed uptrend" check is replaced by ema_spread >= spread_min,
  // turning `spread` into a two-sided band (e.g. spread_min=-4 spread=4 → ±4%
  // around the EMA crossover). When omitted, behavior is unchanged (fast>slow).
  spread_min: args.spread_min !== undefined ? Number(args.spread_min) : null,
  adr: num("adr", 1),
  value: num("value", 5000000),
};

function readJson(spec) {
  const raw = spec === "-" ? readFileSync(0, "utf8") : readFileSync(spec, "utf8");
  return JSON.parse(raw);
}

// ---------- formatting helpers ----------
const REIT_RE = /REIT|Fund|ETF|Sukuk/i;

function compact(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toFixed(0);
}

// fraction (0.40) -> "40.0%"
function pctFrac(x, d = 1) {
  if (x == null || Number.isNaN(x)) return "—";
  return (x * 100).toFixed(d) + "%";
}

// signed fraction (0.413) -> "+41.3%"
function pctFracSigned(x, d = 1) {
  if (x == null || Number.isNaN(x)) return "—";
  return (x > 0 ? "+" : "") + (x * 100).toFixed(d) + "%";
}

// already-a-percent (110.5) -> "+110.5%"
function pctVal(x, d = 1, signed = true) {
  if (x == null || Number.isNaN(x)) return "—";
  return (signed && x > 0 ? "+" : "") + x.toFixed(d) + "%";
}

// Escape a single CSV cell (RFC-4180: quote if it contains comma, quote, or newline).
function csvCell(s) {
  s = String(s);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

// ---------- compact cell formatters (screen grid only; CSV keeps full values) ----------
function trunc(s, max) {
  s = String(s);
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}
// price: 2 decimals under 100, 1 decimal at/above (saves a column char)
function closec(x) {
  if (x == null || Number.isNaN(x)) return "—";
  return Math.abs(x) >= 100 ? x.toFixed(1) : x.toFixed(2);
}
// daily change: 1 decimal + %, minus sign kept, no plus sign
function chgc(x) {
  if (x == null || Number.isNaN(x)) return "—";
  return x.toFixed(1) + "%";
}
// percent already in percent units: drop decimals at/above 100, else 1 decimal; no % / + sign
function cpct(x) {
  if (x == null || Number.isNaN(x)) return "—";
  return Math.abs(x) >= 100 ? String(Math.round(x)) : x.toFixed(1);
}
const cpctFrac = (x) => (x == null || Number.isNaN(x) ? "—" : cpct(x * 100));
// big counts: M = 1 decimal, K = integer
function volc(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return Math.round(n / 1e3) + "K";
  return String(Math.round(n));
}
// market cap / money: B = 1 decimal, M/K = integer
function capc(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (a >= 1e6) return Math.round(n / 1e6) + "M";
  if (a >= 1e3) return Math.round(n / 1e3) + "K";
  return String(Math.round(n));
}
const valc = (n) => (n == null || Number.isNaN(n) ? "—" : "SAR" + capc(n));

// Render a continuous box-drawing grid (┌┬┐ ├┼┤ └┴┘ │ ─).
// headers: string[]; rows: string[][]; aligns: ("l"|"r")[] per column.
function renderGrid(headers, rows, aligns) {
  const w = headers.map((h, i) =>
    Math.max(h.length, ...rows.map((r) => r[i].length)),
  );
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
  return {
    text: [top, fmtRow(headers), mid, ...rows.map(fmtRow), bot].join("\n"),
    width: top.length,
  };
}

// ---------- stage: filter ----------
function stageFilter() {
  if (!args.input) throw new Error("stage=filter requires input=<screen.json|->");
  const data = readJson(args.input);
  const stocks = data.stocks || [];
  const fastKey = "EMA" + params.ema_fast;
  const slowKey = "EMA" + params.ema_slow;

  const gainF = params.gain / 100;
  const spreadF = params.spread / 100;
  const spreadMinF = params.spread_min != null ? params.spread_min / 100 : null;
  const adrF = params.adr / 100;

  const matches = [];
  const skipped = [];

  for (const s of stocks) {
    const code = String(s.symbol).split(":")[1] || "";
    if (code.startsWith("9")) continue; // Nomu / parallel market / ETFs
    if (REIT_RE.test(s.description || "")) continue; // REITs survive server type filter

    const close = s.close;
    const low = s.price_52_week_low;
    const atr = s.ATR;
    const fast = s[fastKey];
    const slow = s[slowKey];
    const avgVol = s.average_volume_30d_calc;

    if ([close, low, atr, fast, slow, avgVol].some((v) => v == null)) {
      skipped.push({ symbol: s.symbol, description: s.description });
      continue;
    }

    const gain_from_low = close / low - 1;
    const ema_spread = fast / slow - 1;
    const adr_pct = atr / close;
    const avg_value = avgVol * close;

    if (gain_from_low < gainF) continue;
    if (!(close > slow)) continue; // re-verify (server-side enforced)
    if (spreadMinF != null) {
      if (ema_spread < spreadMinF) continue; // two-sided band: lower bound
    } else {
      if (!(fast > slow)) continue; // confirmed uptrend (server-side enforced)
    }
    if (ema_spread > spreadF) continue;
    if (adr_pct < adrF) continue;
    if (avg_value < params.value) continue;

    matches.push({
      symbol: s.symbol,
      description: s.description,
      close,
      gain_from_low,
      ema_spread,
      adr_pct,
      avg_value,
      avg_vol: avgVol,
    });
  }

  matches.sort((a, b) => b.gain_from_low - a.gain_from_low);

  process.stdout.write(
    JSON.stringify(
      {
        params,
        total_count: data.total_count ?? stocks.length,
        screened_count: stocks.length,
        matches,
        skipped,
      },
      null,
      2,
    ) + "\n",
  );
}

// ---------- stage: report ----------
// 17 columns, in the required fixed order. HEADERS = full (CSV); SHORT = on-screen grid.
const HEADERS = [
  "Symbol",
  "Company",
  "Close",
  "Chg %",
  "Vol",
  "Rel Vol",
  "Avg Traded Value",
  "Gain From 52W Low",
  "EMA Spread %",
  "ADR % (ATR/close)",
  "Perf 3M",
  "Perf 1Y",
  "Perf 5Y",
  "Perf 10Y",
  "Perf All",
  "Mkt Cap",
  "Sector",
];
const SHORT = ["Sym", "Name", "Close", "Chg", "Vol", "RVol", "Val", "Low%", "Sprd", "ADR", "3M", "1Y", "5Y", "10Y", "All", "Cap", "Sec"];
const ALIGN = ["l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "l"];
const NAME_MAX = 20; // truncate Company
const SEC_MAX = 11; // truncate Sector

// Separator between the fixed-width report (table + summary, which the command wraps
// in a ```text code block) and the clickable markdown chart-links list (which MUST be
// printed OUTSIDE the code block so the links render). The command splits stdout on
// this exact line, prints the part before it verbatim inside the fence, and prints the
// part after it as normal markdown. The sentinel line itself is never shown.
const LINKS_SENTINEL = "===CHART_LINKS===";
// TradingView interactive chart URL for a TADAWUL symbol.
// Symbol-page URL: plain dash path, no query string / special chars — robust in every
// terminal & chat link parser (the ?symbol=TADAWUL:1234 form broke on the ":").
const chartUrl = (sym) => `https://www.tradingview.com/symbols/${sym.replace(":", "-")}/`;

function stageReport() {
  if (!args.filtered) throw new Error("stage=report requires filtered=<filter.json|->");
  if (!args.lookup) throw new Error("stage=report requires lookup=<lookup.json|->");
  const filtered = readJson(args.filtered);
  const lookup = readJson(args.lookup);
  const p = filtered.params || params;
  const csvPath = args.csv || ".claude/outputs/saudi-momentum.csv";

  const bySym = new Map();
  for (const d of lookup.symbols || []) bySym.set(d.symbol, d);

  const rows = filtered.matches.map((m) => ({ ...m, d: bySym.get(m.symbol) || {} }));

  // CSV cells: FULL, untruncated values (full symbol/company/sector, signed %, "SAR 68.9M").
  const csvRows = rows.map((r) => {
    const d = r.d;
    return [
      r.symbol,
      r.description,
      r.close.toFixed(2),
      pctVal(d.change, 2),
      compact(d.volume),
      d.relative_volume_10d_calc != null ? d.relative_volume_10d_calc.toFixed(2) : "—",
      "SAR " + compact(r.avg_value),
      pctFracSigned(r.gain_from_low, 1),
      pctFrac(r.ema_spread, 2),
      pctFrac(r.adr_pct, 2),
      pctVal(d["Perf.3M"], 1),
      pctVal(d["Perf.Y"], 1),
      pctVal(d["Perf.5Y"], 1),
      pctVal(d["Perf.10Y"], 1),
      pctVal(d["Perf.All"], 1),
      compact(d.market_cap_basic),
      d.sector || "—",
    ];
  });

  // ----- write CSV (Excel-friendly, with UTF-8 BOM) -----
  const csv =
    "﻿" +
    [HEADERS, ...csvRows].map((row) => row.map(csvCell).join(",")).join("\r\n") +
    "\r\n";
  mkdirSync(dirname(csvPath), { recursive: true });
  writeFileSync(csvPath, csv);

  // Grid cells: COMPACT, truncated values so all 17 columns fit one screen table.
  const gridRows = rows.map((r) => {
    const d = r.d;
    return [
      r.symbol.replace(/^TADAWUL:/, ""),
      trunc(r.description, NAME_MAX),
      closec(r.close),
      chgc(d.change),
      volc(d.volume),
      d.relative_volume_10d_calc != null ? d.relative_volume_10d_calc.toFixed(2) : "—",
      valc(r.avg_value),
      cpctFrac(r.gain_from_low),
      cpctFrac(r.ema_spread),
      cpctFrac(r.adr_pct),
      cpct(d["Perf.3M"]),
      cpct(d["Perf.Y"]),
      cpct(d["Perf.5Y"]),
      cpct(d["Perf.10Y"]),
      cpct(d["Perf.All"]),
      capc(d.market_cap_basic),
      trunc(d.sector || "—", SEC_MAX),
    ];
  });

  const grid = renderGrid(SHORT, gridRows, ALIGN);

  // Width guard (rule 9): if a max width is set and the grid exceeds it, stop and report.
  const maxWidth = args.maxwidth ? Number(args.maxwidth) : 0;
  if (maxWidth > 0 && grid.width > maxWidth) {
    process.stdout.write(
      `WIDTH PROBLEM: the drawn grid is ${grid.width} columns wide, which exceeds the ` +
        `requested maxwidth=${maxWidth}. Not printing a broken/wrapped table.\n` +
        `Full results are in the CSV: ${csvPath}\n` +
        `Options: widen the terminal, lower NAME_MAX/SEC_MAX in the script, or approve splitting the table.\n`,
    );
    return;
  }

  // ----- box-grid table to stdout, then short summary -----
  const out = [];
  out.push(grid.text);
  out.push("");
  if (rows.length === 0) out.push("No matches.");

  // ----- short summary -----
  out.push(`Matches: ${rows.length} of ${filtered.total_count} server-screened TADAWUL stocks.`);

  if (rows.length) {
    const top = rows
      .slice(0, 3)
      .map((r) => `${r.description} (${r.symbol.split(":")[1]}, ${pctFracSigned(r.gain_from_low, 1)})`);
    out.push(`Strongest 3 (by gain from 52W low): ${top.join("; ")}.`);
  }

  const floorFlags = rows.filter((r) => r.avg_value <= p.value * 1.2);
  const thinFlags = rows.filter((r) => r.avg_vol < 200000 && r.avg_value > p.value * 1.2);
  const liq = [];
  if (floorFlags.length)
    liq.push(
      `within ~20% of the SAR ${compact(p.value)} value floor — ${floorFlags
        .map((r) => `${r.symbol.split(":")[1]} (SAR ${compact(r.avg_value)})`)
        .join(", ")}`,
    );
  if (thinFlags.length)
    liq.push(
      `thin share volume (<200K/day, clearing the floor mainly on price) — ${thinFlags
        .map((r) => `${r.symbol.split(":")[1]} (~${compact(r.avg_vol)} sh/day)`)
        .join(", ")}`,
    );
  out.push(`Liquidity warnings: ${liq.length ? liq.join("; ") + "." : "none."}`);

  const skipped = filtered.skipped || [];
  out.push(
    `Missing-data warnings: ${
      skipped.length ? skipped.map((s) => `${s.symbol} (${s.description})`).join(", ") + "." : "none."
    }`,
  );

  out.push("Scope: Saudi Main Market (TADAWUL) only — Nomu/parallel-market (9xxx), ETFs, and REITs/funds excluded.");
  out.push(`CSV: ${csvPath}`);

  // ----- chart-links section (rendered OUTSIDE the code block by the command) -----
  out.push(LINKS_SENTINEL);
  if (rows.length) {
    out.push("**Open chart (click a symbol):**");
    out.push("");
    rows.forEach((r, i) => {
      const code = r.symbol.split(":")[1];
      out.push(`${i + 1}. [${code} — ${trunc(r.description, 40)}](${chartUrl(r.symbol)})`);
    });
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
  process.stderr.write("saudi-momentum.js error: " + err.message + "\n");
  process.exit(1);
}
