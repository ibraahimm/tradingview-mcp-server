#!/usr/bin/env node
/**
 * Persistent cohort tracker for the /saudi-stage2 (TASI-W1, "first wave") and /saudi-wave2 (TASI-W2,
 * "second wave / continuation") slash commands.
 *
 * One UNIFIED journey per symbol across both waves: a name can first appear in TASI-W1, later in
 * TASI-W2, and that is treated as a single continuous journey. The ledger is an append-only JSONL
 * event log (one line per symbol-per-run) at .claude/outputs/saudi-tracker.jsonl. CSV is an
 * optional export only — JSONL is the source of truth.
 *
 * Two stages:
 *   1) ingest — input: a wave's stage=filter JSON ({ params, matches:[...] }). Stamps today's
 *               date + source (TASI-W1|TASI-W2) + each match's metrics into the ledger. Each event is made
 *               self-contained by carrying first_close / first_seen / first_source, derived from
 *               the EARLIEST prior event for that symbol (so the journey origin is stable).
 *   2) report — reads the whole ledger, rolls every symbol's events into one journey, classifies
 *               its lifecycle state, and prints a box-grid + summary (and an optional CSV export).
 *
 * Lifecycle (one primary state per symbol, precedence top-down):
 *   FAILED     : latest EMA reading shows close < first_close AND close < EMA200 (vs200 < 0)
 *                — underwater from the original signal AND the long trend is broken.
 *   GRADUATED  : Perf.5Y > grad_p5y (default 2000) — the long-run big-winner flag (name kept).
 *   EXPIRED    : age since first_seen > horizon_days (default 1826 ≈ 5y) and not graduated.
 *   STALE      : not seen on either screen for > stale_days (default 120) — dropped off the radar.
 *   ACTIVE-TASI-W2  : still appearing, most recent appearance was TASI-W2.
 *   ACTIVE-TASI-W1  : still appearing, most recent appearance was TASI-W1 (never reached TASI-W2).
 * Badges (orthogonal, shown in the summary): NEW (first appeared in the latest run),
 *   PROMOTED (appeared in BOTH TASI-W1 and TASI-W2 — the TASI-W1→TASI-W2 progression), nearATH (belowATH < 10).
 *
 * Progress metrics:
 *   gainSinceSignal = (close / first_close - 1) * 100   // main progress: P&L from first signal
 *   belowATH                                            // structural recovery toward the ATH
 *
 * Note: the TASI-W1 (/saudi-stage2) screen does not fetch EMAs, so TASI-W1-only names carry no EMA200 /
 * vs200. The FAILED rule needs that reading, so it is evaluated from the most recent EMA-bearing
 * (i.e. TASI-W2) event; a name that has only ever appeared in TASI-W1 cannot be marked FAILED yet.
 *
 * Usage:
 *   node saudi-tracker.js stage=ingest filtered=<wave_filter.json> source=TASI-W1|TASI-W2 [date=YYYY-MM-DD] [ledger=path]
 *   node saudi-tracker.js stage=report [ledger=path] [grad_p5y=2000] [stale_days=120] [horizon_days=1826] [csv=path]
 */

import { readFileSync, writeFileSync, appendFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";

// ---------- arg parsing (key=value tokens) ----------
const args = {};
for (const tok of process.argv.slice(2)) {
  const eq = tok.indexOf("=");
  if (eq === -1) continue;
  args[tok.slice(0, eq)] = tok.slice(eq + 1);
}
const num = (k, def) => (args[k] !== undefined ? Number(args[k]) : def);
const DEFAULT_LEDGER = ".claude/outputs/saudi-tracker.jsonl";

function readJson(spec) {
  const raw = spec === "-" ? readFileSync(0, "utf8") : readFileSync(spec, "utf8");
  return JSON.parse(raw);
}
function readLedger(path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

// ---------- value helpers ----------
const numOrNull = (v) => (v == null || Number.isNaN(v) ? null : v);
const round = (x, p) => (x == null || Number.isNaN(x) ? null : Math.round(x * 10 ** p) / 10 ** p);
const today = () => new Date().toISOString().slice(0, 10);
const dayMs = 86400000;

// ---------- formatting helpers ----------
const LINKS_SENTINEL = "===CHART_LINKS===";
const chartUrl = (sym) => `https://www.tradingview.com/chart/?symbol=${sym}`;
const r1 = (x) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(1));
const pr = (x) => (x == null || Number.isNaN(x) ? "—" : Math.abs(x) >= 100 ? x.toFixed(1) : x.toFixed(2));
const sgn = (x) => (x == null || Number.isNaN(x) ? "—" : (x >= 0 ? "+" : "") + x.toFixed(1));
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

// ---------- stage: ingest ----------
function stageIngest() {
  if (!args.filtered) throw new Error("stage=ingest requires filtered=<wave_filter.json|->");
  const source = String(args.source || "").toUpperCase();
  if (source !== "TASI-W1" && source !== "TASI-W2") throw new Error("stage=ingest requires source=TASI-W1|TASI-W2");
  const date = args.date || today();
  const ledgerPath = args.ledger || DEFAULT_LEDGER;
  const data = readJson(args.filtered);
  const matches = data.matches || [];

  // Derive each symbol's journey origin from prior events (stable, self-contained stamping).
  const first = new Map(); // symbol -> { first_close, first_seen, first_source }
  const priorSources = new Map(); // symbol -> Set<source>
  for (const e of readLedger(ledgerPath)) {
    if (!first.has(e.symbol)) {
      first.set(e.symbol, {
        first_close: e.first_close ?? e.close,
        first_seen: e.first_seen ?? e.date,
        first_source: e.first_source ?? e.source,
      });
    }
    if (!priorSources.has(e.symbol)) priorSources.set(e.symbol, new Set());
    priorSources.get(e.symbol).add(e.source);
  }

  const ts = Date.parse(date + "T00:00:00Z");
  const events = [];
  let nNew = 0,
    nPromoted = 0;
  for (const m of matches) {
    const sym = m.symbol;
    const f = first.get(sym);
    if (!f) nNew++;
    const seen = priorSources.get(sym) || new Set();
    if (source === "TASI-W2" && seen.has("TASI-W1") && !seen.has("TASI-W2")) nPromoted++;
    events.push({
      date,
      ts,
      source,
      symbol: sym,
      name: m.description,
      close: round(m.close, 2),
      first_close: round(f ? f.first_close : m.close, 2),
      first_seen: f ? f.first_seen : date,
      first_source: f ? f.first_source : source,
      belowATH: round(m.belowATH, 1),
      offLow: round(m.offLow, 1),
      DDmax: round(m.DDmax, 1),
      nrHi: round(m.nrHi, 1),
      "Perf.1M": numOrNull(m["Perf.1M"]),
      "Perf.3M": numOrNull(m["Perf.3M"]),
      "Perf.6M": numOrNull(m["Perf.6M"]),
      "Perf.1Y": numOrNull(m["Perf.Y"]),
      "Perf.3Y": numOrNull(m["Perf.3Y"]),
      "Perf.5Y": numOrNull(m["Perf.5Y"]),
      ema21gap: numOrNull(m.ema21gap),
      emaComp: numOrNull(m.emaComp),
      ext60: numOrNull(m.ext60),
      vs200: numOrNull(m.vs200),
      tag: m.tag ?? null,
    });
  }
  mkdirSync(dirname(ledgerPath), { recursive: true });
  if (events.length) appendFileSync(ledgerPath, events.map((e) => JSON.stringify(e)).join("\n") + "\n");
  process.stdout.write(
    `Ingested ${events.length} ${source} match(es) dated ${date} → ${ledgerPath} ` +
      `(${nNew} new symbol(s), ${nPromoted} promoted TASI-W1→TASI-W2).\n`,
  );
}

// ---------- stage: report ----------
const HEAD = ["Sym", "Name", "First", "Jrny", "Rns", "Entry", "Now", "Gain%", "bATH", "offL", "5Y", "v200", "State"];
const ALIGN = ["l", "l", "l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "l"];
const NAME_MAX = 20;

function journeyString(evs) {
  const out = [];
  for (const e of evs) if (out[out.length - 1] !== e.source) out.push(e.source);
  return out.join("→");
}

// Roll the ledger into one journey + lifecycle state per symbol. `now` is the as-of epoch (ms):
// wall-clock for the live report, or a fixed as-of for deterministic conformance / PIT replay. This
// is the SINGLE source of the journey/state logic — both stage=report and stage=conform call it, and
// the research Python tracker (research/backtest/tracker.py) is conformed against its output.
function buildItems(ledger, now, { grad_p5y, stale_days, horizon_days }) {
  const bySym = new Map();
  let latestDate = "";
  for (const e of ledger) {
    if (!bySym.has(e.symbol)) bySym.set(e.symbol, []);
    bySym.get(e.symbol).push(e);
    if (e.date > latestDate) latestDate = e.date;
  }
  const items = [];
  for (const [sym, raw] of bySym) {
    const evs = raw.slice().sort((a, b) => a.ts - b.ts);
    const first = evs[0];
    const last = evs[evs.length - 1];
    const first_close = first.first_close ?? first.close;
    const first_seen = first.first_seen ?? first.date;
    const gain = first_close ? (last.close / first_close - 1) * 100 : null;
    const hasW1 = evs.some((e) => e.source === "TASI-W1");
    const hasW2 = evs.some((e) => e.source === "TASI-W2");
    // latest EMA-bearing reading (TASI-W2 events carry vs200)
    let vs200 = null;
    for (let i = evs.length - 1; i >= 0; i--)
      if (evs[i].vs200 != null) {
        vs200 = evs[i].vs200;
        break;
      }
    const p5y = last["Perf.5Y"];
    const ageDays = (now - Date.parse(first_seen + "T00:00:00Z")) / dayMs;
    const sinceLast = (now - Date.parse(last.date + "T00:00:00Z")) / dayMs;

    const gradFlag = p5y != null && p5y > grad_p5y;
    const failed = vs200 != null && last.close < first_close && vs200 < 0;
    const expired = ageDays > horizon_days && !gradFlag;
    const stale = !failed && !gradFlag && sinceLast > stale_days;
    let state;
    if (failed) state = "FAILED";
    else if (gradFlag) state = "GRAD★";
    else if (expired) state = "EXPIRED";
    else if (stale) state = "STALE";
    else state = last.source === "TASI-W2" ? "ACTIVE-TASI-W2" : "ACTIVE-TASI-W1";

    items.push({
      symbol: sym,
      name: last.name,
      first_seen,
      journey: journeyString(evs),
      runs: evs.length,
      first_close,
      close: last.close,
      gain,
      belowATH: last.belowATH,
      offLow: last.offLow,
      p5y,
      vs200,
      state,
      isNew: first_seen === latestDate,
      promoted: hasW1 && hasW2,
      nearATH: last.belowATH != null && last.belowATH < 10,
    });
  }
  items.sort((a, b) => (b.gain ?? -1e9) - (a.gain ?? -1e9));
  return { items, latestDate };
}

// stage=conform — machine-readable per-symbol journey/state, sorted by symbol, for cross-implementation
// (JS↔Python) differential testing. `asof=YYYY-MM-DD` fixes the clock so output is deterministic.
function stageConform() {
  const ledgerPath = args.ledger || DEFAULT_LEDGER;
  const now = args.asof ? Date.parse(args.asof + "T00:00:00Z") : Date.now();
  const { items } = buildItems(readLedger(ledgerPath), now, {
    grad_p5y: num("grad_p5y", 2000), stale_days: num("stale_days", 120), horizon_days: num("horizon_days", 1826),
  });
  const sorted = {};
  for (const r of items.slice().sort((a, b) => (a.symbol < b.symbol ? -1 : a.symbol > b.symbol ? 1 : 0)))
    sorted[r.symbol] = {
      state: r.state, journey: r.journey, runs: r.runs, gain: round(r.gain, 4),
      first_close: r.first_close, close: r.close, belowATH: r.belowATH, offLow: r.offLow,
      p5y: r.p5y, vs200: r.vs200, isNew: r.isNew, promoted: r.promoted, nearATH: r.nearATH,
    };
  process.stdout.write(JSON.stringify(sorted, null, 2) + "\n");
}

function stageReport() {
  const ledgerPath = args.ledger || DEFAULT_LEDGER;
  const grad_p5y = num("grad_p5y", 2000);
  const stale_days = num("stale_days", 120);
  const horizon_days = num("horizon_days", 1826); // ~5 years
  const ledger = readLedger(ledgerPath);
  if (!ledger.length) {
    process.stdout.write(`No tracker ledger yet at ${ledgerPath} — run /saudi-stage2 or /saudi-wave2 (which ingest) first.\n`);
    return;
  }

  const now = args.asof ? Date.parse(args.asof + "T00:00:00Z") : Date.now();
  const { items, latestDate } = buildItems(ledger, now, { grad_p5y, stale_days, horizon_days });

  // optional CSV export of the per-symbol summary
  if (args.csv) {
    const H = ["Symbol", "Name", "First Seen", "Journey", "Runs", "First Close", "Close", "Gain %", "Below ATH %", "Off Low %", "Perf 5Y", "vs EMA200 %", "State", "New", "Promoted", "Near ATH"];
    const rows = items.map((r) => [
      r.symbol, r.name, r.first_seen, r.journey, String(r.runs), pr(r.first_close), pr(r.close), r1(r.gain),
      r1(r.belowATH), r1(r.offLow), r1(r.p5y), r1(r.vs200), r.state, r.isNew ? "yes" : "", r.promoted ? "yes" : "", r.nearATH ? "yes" : "",
    ]);
    const csv = "﻿" + [H, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
    mkdirSync(dirname(args.csv), { recursive: true });
    writeFileSync(args.csv, csv);
  }

  const gridRows = items.map((r) => [
    r.symbol.replace(/^TADAWUL:/, ""), trunc(r.name, NAME_MAX), r.first_seen, r.journey || "—", String(r.runs),
    pr(r.first_close), pr(r.close), sgn(r.gain), r1(r.belowATH), r1(r.offLow), r1(r.p5y), sgn(r.vs200), r.state,
  ]);
  const grid = renderGrid(HEAD, gridRows, ALIGN);

  const maxWidth = args.maxwidth ? Number(args.maxwidth) : 0;
  if (maxWidth > 0 && grid.width > maxWidth) {
    process.stdout.write(`WIDTH PROBLEM: grid is ${grid.width} cols (> maxwidth=${maxWidth}). See CSV.\n`);
    return;
  }

  const count = (st) => items.filter((r) => r.state === st).length;
  const list = (arr) => (arr.length ? arr.map((r) => r.symbol.split(":")[1]).join(", ") : "none");
  const out = [
    `Saudi wave tracker — ${items.length} symbol(s) tracked across ${ledger.length} event(s); latest run ${latestDate}.`,
    "",
    grid.text,
    "",
    `States: ACTIVE-TASI-W1 ${count("ACTIVE-TASI-W1")} · ACTIVE-TASI-W2 ${count("ACTIVE-TASI-W2")} · GRAD★ ${count("GRAD★")} · FAILED ${count("FAILED")} · STALE ${count("STALE")} · EXPIRED ${count("EXPIRED")}.`,
    `New this run (${latestDate}): ${list(items.filter((r) => r.isNew))}.`,
    `Near ATH (belowATH < 10%, descriptor): ${list(items.filter((r) => r.nearATH))}.`,
    `Graduation flag: Perf.5Y > ${grad_p5y}. Failure: close < first signal AND close < EMA200. Horizon: ${horizon_days}d (~${(horizon_days / 365.25).toFixed(1)}y). Stale: ${stale_days}d.`,
    `Ledger: ${ledgerPath}` + (args.csv ? ` · CSV export: ${args.csv}` : ""),
  ];

  // Grouped sections (presentation only — derived from already-computed states/fields).
  const nm = (r, n) => `${r.symbol.split(":")[1]} ${trunc(r.name, n)}`;
  const promoted = items.filter((r) => r.promoted);
  const w2 = items.filter((r) => r.state === "ACTIVE-TASI-W2");
  const w1 = items.filter((r) => r.state === "ACTIVE-TASI-W1");
  const below200 = items.filter((r) => r.vs200 != null && r.vs200 < 0).sort((a, b) => a.vs200 - b.vs200);
  const grad = items.filter((r) => r.state === "GRAD★");
  const failed = items.filter((r) => r.state === "FAILED");
  const stale = items.filter((r) => r.state === "STALE");
  out.push("");
  out.push("── Groups ──");
  out.push(`▸ Promoted TASI-W1→TASI-W2 (${promoted.length}): ${promoted.length ? promoted.map((r) => nm(r, 22)).join("; ") : "none"}`);
  out.push(`▸ Active-TASI-W2 (${w2.length}): ${w2.length ? w2.map((r) => `${nm(r, 16)} (${sgn(r.gain)}%)`).join("; ") : "none"}`);
  out.push(`▸ Active-TASI-W1 (${w1.length}): ${w1.length ? w1.map((r) => r.symbol.split(":")[1]).join(", ") : "none"}`);
  out.push(
    `▸ Below EMA200 watchlist (${below200.length}): ${below200.length ? below200.map((r) => `${r.symbol.split(":")[1]} (${sgn(r.vs200)})`).join(", ") : "none"}`,
  );
  if (grad.length) out.push(`▸ Graduated★ (${grad.length}): ${grad.map((r) => `${nm(r, 18)} (5Y ${r1(r.p5y)})`).join("; ")}`);
  if (failed.length) out.push(`▸ Failed (${failed.length}): ${failed.map((r) => `${nm(r, 16)} (${sgn(r.gain)}%, v200 ${sgn(r.vs200)})`).join("; ")}`);
  if (stale.length) out.push(`▸ Stale (${stale.length}): ${stale.map((r) => nm(r, 20)).join("; ")}`);

  out.push(LINKS_SENTINEL);
  out.push("**Open chart (click a symbol):**");
  out.push("");
  items.forEach((r) => out.push(`${r.symbol.split(":")[1]} ${trunc(r.name, 34)} [${r.state}]: [open chart](${chartUrl(r.symbol)})`));

  process.stdout.write(out.join("\n") + "\n");
}

// ---------- dispatch ----------
const stage = args.stage || "report";
try {
  if (stage === "ingest") stageIngest();
  else if (stage === "report") stageReport();
  else if (stage === "conform") stageConform();
  else throw new Error(`unknown stage='${stage}' (expected ingest|report|conform)`);
} catch (err) {
  process.stderr.write("saudi-tracker.js error: " + err.message + "\n");
  process.exit(1);
}
