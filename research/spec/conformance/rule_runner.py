#!/usr/bin/env python3
"""Rule-vector conformance runner (CI-friendly).

Validates every fixture under ../rule_vectors/ against the rule engine
(research.engine.rules): the engine's (passed, first_fail) for each candidate must equal the
frozen expectation, the row-wise and frame-wise paths must agree, every case's spec_version must
match ../VERSION, and every rule in rules.yaml must have >=1 covering case.

    python research/spec/conformance/rule_runner.py
Exit 0 = all pass; non-zero = at least one failure.
"""
from __future__ import annotations
import csv, json, os, sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent          # research/spec
VECTORS = SPEC / "rule_vectors"
VERSION = (SPEC / "VERSION").read_text().strip()

sys.path.insert(0, os.getcwd())                          # make research.* importable from repo root
from research.engine import rules as R                   # noqa: E402

import polars as pl                                      # noqa: E402


def _cell(v):
    return None if v == "" else float(v)


def _read(p):
    with p.open() as fh:
        return list(csv.DictReader(fh))


def run_case(cdir: Path, rules: dict) -> list[str]:
    case = json.loads((cdir / "case.json").read_text())
    fails = []
    if case["spec_version"] != VERSION:
        fails.append(f"{cdir.name}: spec_version {case['spec_version']} != VERSION {VERSION}")
    rule = rules[case["rule"]]
    overrides = case.get("params_overrides")
    inp = _read(cdir / case["input_file"])
    exp = _read(cdir / case["expected_file"])

    # feature columns = everything except the label
    feat_cols = [c for c in inp[0].keys() if c != "label"]
    rows = [{c: _cell(r[c]) for c in feat_cols} for r in inp]

    # 1. row-wise evaluate vs frozen expectation
    got = [R.evaluate(rule, row, overrides) for row in rows]
    for i, (e, (passed, ff)) in enumerate(zip(exp, got)):
        exp_pass = e["pass"].strip().lower() == "true"
        exp_ff = e["first_fail"] or None
        if passed != exp_pass or ff != exp_ff:
            fails.append(f"{cdir.name}[{e['label']}]: got (pass={passed}, first_fail={ff}) "
                         f"!= exp (pass={exp_pass}, first_fail={exp_ff})")

    # 2. frame-wise path must agree with row-wise
    df = pl.DataFrame(rows)
    fr = R.evaluate_frame(rule, df, overrides)
    for i, (passed, ff) in enumerate(got):
        if fr["passed"][i] != passed or fr["first_fail"][i] != ff:
            fails.append(f"{cdir.name}[row {i}]: evaluate_frame disagrees with evaluate")
    return fails


def main() -> int:
    rules = R.load_rules()
    cases = sorted(d for d in VECTORS.iterdir() if d.is_dir() and not d.name.startswith("_"))
    fails = []
    covered = set()
    for cdir in cases:
        case = json.loads((cdir / "case.json").read_text())
        covered.add(case["rule"])
        fails += run_case(cdir, rules)
    for r in rules:
        if r not in covered:
            fails.append(f"coverage: rule {r} has no rule_vector case")

    if fails:
        print(f"FAIL ({len(fails)} issue(s)):")
        for f in fails:
            print("  -", f)
        return 1
    print(f"PASS: {len(cases)} rule case(s) across {sorted(covered)}, spec_version {VERSION}, coverage OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
