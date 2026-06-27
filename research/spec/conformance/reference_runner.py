#!/usr/bin/env python3
"""Golden-vector conformance runner (stdlib-only, CI-friendly).

Validates every case under ../vectors/ against a reference implementation of the spec's
FUNCTIONS, enforces coverage + spec_version, and exits non-zero on any failure.

The built-in reference implementation makes the vectors self-validating today. Production CI
ALSO drives the Python engine adapter and the TS adapter via --adapter (see runner_contract.md);
all implementations must agree with the frozen expected values.

Usage:
    python reference_runner.py
    python reference_runner.py --adapter some.module:FUNCTIONS
"""
from __future__ import annotations
import csv, json, sys, re, os, calendar, importlib
from datetime import date, timedelta
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent          # research/spec
VECTORS = SPEC_DIR / "vectors"
VERSION = (SPEC_DIR / "VERSION").read_text().strip()


# ---------------- reference implementation of FUNCTIONS ----------------
def ema(closes, params):
    length = int(params["length"])
    alpha = 2.0 / (length + 1.0)
    out, prev = [], None
    for i, c in enumerate(closes):
        prev = c if prev is None else alpha * c + (1 - alpha) * prev
        out.append(prev if (i + 1) >= length else None)  # null until warmup satisfied
    return out


def _sub_months(d: date, months: int) -> date:
    total = (d.year * 12 + (d.month - 1)) - months
    y, m = total // 12, total % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def perf_calendar(rows, params):
    months = int(params["months"])
    dates = [date.fromisoformat(r["date"]) for r in rows]
    closes = [float(r["close"]) for r in rows]
    out = []
    for i in range(len(rows)):
        target = _sub_months(dates[i], months)
        ref = None
        for j in range(i, -1, -1):           # as-of-or-before: last bar with date <= target
            if dates[j] <= target:
                ref = closes[j]
                break
        out.append(None if ref is None else (closes[i] / ref - 1) * 100.0)
    return out


def _f(row, k):
    v = row.get(k, "")
    return None if v == "" else float(v)


def ratios(row):
    close, ath = _f(row, "close"), _f(row, "ath")
    lo, hi = _f(row, "low_52w"), _f(row, "high_52w")
    e21, e60, e200 = _f(row, "ema21"), _f(row, "ema60"), _f(row, "ema200")
    pct = lambda x: None if x is None else x
    return {
        "ddmax":    None if None in (ath, lo) else (ath - lo) / ath * 100,
        "below_ath":None if None in (ath, close) else (ath - close) / ath * 100,
        "off_low":  None if None in (close, lo) else (close / lo - 1) * 100,
        "nrhi":     None if None in (close, hi) else close / hi * 100,
        "ext60":    None if None in (close, e60) else (close / e60 - 1) * 100,
        "ema21gap": None if None in (close, e21) else (close / e21 - 1) * 100,
        "ema_comp": None if None in (e21, e60) else (e21 / e60 - 1) * 100,
        "vs200":    None if None in (close, e200) else (close / e200 - 1) * 100,
    }


def _sub_years(d: date, years: int) -> date:
    y = d.year - int(years)
    return date(y, d.month, min(d.day, calendar.monthrange(y, d.month)[1]))


def running_max(rows, params):
    field = params.get("field", "high")
    lb = params.get("lookback_years")
    dates = [date.fromisoformat(r["date"]) for r in rows]
    vals = [float(r[field]) for r in rows]
    out = []
    for i in range(len(rows)):
        if lb:
            start = _sub_years(dates[i], lb)
            window = [vals[j] for j in range(i + 1) if dates[j] >= start]
        else:
            window = vals[: i + 1]               # all-time running max from the first bar
        out.append(max(window))
    return out


def rolling_extreme(rows, params):
    field, weeks, op = params["field"], int(params["weeks"]), params["op"]
    dates = [date.fromisoformat(r["date"]) for r in rows]
    vals = [float(r[field]) for r in rows]
    out = []
    for i in range(len(rows)):
        start = dates[i] - timedelta(days=weeks * 7)     # window [date - weeks*7d, date], inclusive
        window = [vals[j] for j in range(i + 1) if dates[j] >= start]
        out.append(max(window) if op == "max" else min(window))
    return out


REFERENCE_FUNCTIONS = {
    "ema": ema,
    "perf_calendar": perf_calendar,
    "running_max": running_max,
    "rolling_extreme": rolling_extreme,
    "ratios": ratios,
}


# ---------------- harness ----------------
def _read_csv(p: Path):
    with p.open() as fh:
        return list(csv.DictReader(fh))


def _num(cell):
    return None if cell is None or cell == "" else float(cell)


def _eq(got, exp, tol):
    if got is None or exp is None:
        return got is None and exp is None
    if abs(got - exp) <= tol.get("abs", 0):
        return True
    rel = tol.get("rel", 0.0)
    return rel > 0 and abs(got - exp) <= rel * abs(exp)


def run_case(cdir: Path, funcs) -> list[str]:
    case = json.loads((cdir / "case.json").read_text())
    fails = []
    if case["spec_version"] != VERSION:
        fails.append(f"{cdir.name}: spec_version {case['spec_version']} != VERSION {VERSION}")
    tgt, tol = case["target"], case["tolerance"]
    rows = _read_csv(cdir / case["input_file"])
    exp = _read_csv(cdir / case["expected_file"])
    fid = tgt["id"]

    if tgt["kind"] == "function":
        params = tgt.get("params", {})
        # ema consumes a close series; perf_calendar / running_max / rolling_extreme consume rows.
        got = funcs["ema"]([float(r["close"]) for r in rows], params) if fid == "ema" else funcs[fid](rows, params)
        out_col = next(c for c in exp[0].keys() if c not in ("idx", "date"))   # the single output column
        for i, e in enumerate(exp):
            if not _eq(got[i], _num(e[out_col]), tol):
                fails.append(f"{cdir.name}[idx{i}].{out_col}: got {got[i]} != exp {e[out_col]!r}")
    elif tgt["kind"] == "expr" and fid == "ratios":
        cols = [c for c in exp[0].keys() if c != "idx"]
        for i, (r, e) in enumerate(zip(rows, exp)):
            got = funcs["ratios"](r)
            for c in cols:
                if not _eq(got.get(c), _num(e[c]), tol):
                    fails.append(f"{cdir.name}[idx{i}].{c}: got {got.get(c)} != exp {e[c]!r}")
    else:
        fails.append(f"{cdir.name}: unsupported target {tgt}")
    return fails


def coverage_check() -> list[str]:
    """Every `vectors:` id referenced in features.yaml must resolve to a case directory."""
    text = (SPEC_DIR / "features.yaml").read_text()
    referenced = set()
    for m in re.finditer(r"vectors:\s*\[([^\]]*)\]", text):
        referenced |= {x.strip() for x in m.group(1).split(",") if x.strip()}
    missing = [v for v in sorted(referenced) if not (VECTORS / v).is_dir()]
    return [f"coverage: feature references vector '{v}' but no case dir exists" for v in missing]


def main() -> int:
    funcs = REFERENCE_FUNCTIONS
    argv = sys.argv[1:]
    spec = None
    for i, a in enumerate(argv):
        if a.startswith("--adapter"):
            spec = a.split("=", 1)[1] if "=" in a else (argv[i + 1] if i + 1 < len(argv) else "")
    if spec:
        sys.path.insert(0, os.getcwd())          # make repo-root packages (research.*) importable
        mod, attr = spec.rsplit(":", 1)
        funcs = getattr(importlib.import_module(mod), attr)
        print(f"(driving adapter {spec})")

    fails = coverage_check()
    cases = sorted(d for d in VECTORS.iterdir() if d.is_dir() and not d.name.startswith("_"))
    for cdir in cases:
        fails += run_case(cdir, funcs)

    if fails:
        print(f"FAIL ({len(fails)} issue(s)):")
        for f in fails:
            print("  -", f)
        return 1
    print(f"PASS: {len(cases)} case(s), spec_version {VERSION}, coverage OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
