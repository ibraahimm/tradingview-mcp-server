#!/usr/bin/env python3
"""Methodology parity gate: the live screener scripts (.claude/scripts/saudi-stage2.js, saudi-wave2.js)
and the canonical research spec (research/spec/rules.yaml) MUST agree on every gate parameter.

These are two hand-maintained implementations of the same methodology; they have drifted before
(the ext60 cap once lived in rules.yaml but not the JS). This gate parses the JS param defaults and
compares them to rules.yaml, so any change made to one side without the other FAILS CI — i.e. a change
to the actual rule spec is guaranteed to be reflected in the research engine (and vice-versa).

    python research/spec/conformance/methodology_parity.py
Exit 0 = live JS and rules.yaml agree on W1/W2 params; non-zero = drift.

SCOPE / LIMITATION: this checks PARAMETER VALUE parity, NOT full behavioral equivalence. A change to
gate LOGIC (an operator, or the funnel order) that doesn't change a parameter value would not be caught
here — closing that needs a JS<->engine behavioral differential on shared fixtures (cf. selftest_tracker).
It has zero awareness of research/ analysis or experiment scripts, so it never blocks experimentation
(experiments use runtime overrides, which don't touch the compared files). See research/spec/TESTING.md.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RULES = yaml.safe_load((ROOT / "research/spec/rules.yaml").read_text())["rules"]
JS = {"W1": ROOT / ".claude/scripts/saudi-stage2.js",
      "W2": ROOT / ".claude/scripts/saudi-wave2.js"}
# Command docs: their Step-2 server-side `(default N)` annotations mirror rules.yaml defaults for the
# coarse pre-filter. Tier-1 SSOT lint (decisions.md D-2026-07-02-03) guards them against drift.
DOCS = {"W1": ROOT / ".claude/commands/saudi-stage2.md",
        "W2": ROOT / ".claude/commands/saudi-wave2.md",
        "W3": ROOT / ".claude/commands/saudi-wave3.md"}
# Per-rule minimum Step-2 (default N) annotation counts, locked to the verified 2026-07-02 state
# (D-2026-07-02-03 addendum): a silently removed annotation must FAIL the gate, not shrink coverage.
# W3 Step-2 uses only value:<param> placeholders (no canon literals) -> 0 is complete, not a gap.
MIN_DOC_DEFAULTS = {"W1": 3, "W2": 9, "W3": 0}

# JS object-key -> rules.yaml param name (only the few that differ)
RENAME = {"offlow": "offlow_min", "value": "value_min"}


def js_params(path: Path) -> dict:
    """Extract the `const params = { ... }` defaults: {param_name: number}."""
    txt = path.read_text()
    block = re.search(r"const params = \{(.*?)\n\};", txt, re.S)
    if not block:
        raise SystemExit(f"could not find params block in {path}")
    out = {}
    for key, val in re.findall(r"(\w+):\s*num\(\"[\w]+\",\s*(-?\d+(?:\.\d+)?)\)", block.group(1)):
        out[RENAME.get(key, key)] = float(val)
    return out


def doc_step2_params(path: Path) -> dict:
    """Extract a command doc's Step-2 server-side `(default N)` annotations: {param: number}.
    Matches lines like `... value:<p6m_min> } `  (default -30)`. Param placeholders use the
    rules.yaml names directly. These mirror canon and were previously an UNGUARDED duplication."""
    txt = path.read_text()
    return {key: float(val) for key, val in
            re.findall(r"value:<(\w+)>[^\n]*?\(default\s+(-?\d+(?:\.\d+)?)", txt)}


def main() -> int:
    fails = []
    for rule in ("W1", "W2"):
        spec = {k: float(v) for k, v in RULES[rule]["params"].items()}
        live = js_params(JS[rule])
        only_spec = set(spec) - set(live)
        only_live = set(live) - set(spec)
        if only_spec:
            fails.append(f"{rule}: params in rules.yaml but NOT in {JS[rule].name}: {sorted(only_spec)}")
        if only_live:
            fails.append(f"{rule}: params in {JS[rule].name} but NOT in rules.yaml: {sorted(only_live)}")
        for k in sorted(set(spec) & set(live)):
            if abs(spec[k] - live[k]) > 1e-9:
                fails.append(f"{rule}.{k}: rules.yaml={spec[k]} != live JS={live[k]}")
        if not (only_spec or only_live):
            print(f"  {rule}: {len(spec)} params — live JS == rules.yaml "
                  f"({'MISMATCH' if any(f.startswith(rule + '.') for f in fails) else 'OK'})")

    # Tier-1 SSOT lint: command-doc Step-2 (default N) annotations vs rules.yaml (D-2026-07-02-03).
    for rule in ("W1", "W2", "W3"):
        spec = {k: float(v) for k, v in RULES[rule]["params"].items()}
        doc = doc_step2_params(DOCS[rule])
        short = len(doc) < MIN_DOC_DEFAULTS[rule]
        if short:
            fails.append(f"{rule} doc: Step-2 (default) coverage shrank — {len(doc)} < min "
                         f"{MIN_DOC_DEFAULTS[rule]} (annotation removed? see decisions.md D-2026-07-02-03)")
        unknown = sorted(set(doc) - set(spec))
        if unknown:
            fails.append(f"{rule} doc: Step-2 (default) for param(s) not in rules.yaml: {unknown}")
        mism = [k for k in sorted(set(doc) & set(spec)) if abs(doc[k] - spec[k]) > 1e-9]
        for k in mism:
            fails.append(f"{rule} doc.{k}: {DOCS[rule].name} (default {doc[k]}) != rules.yaml {spec[k]}")
        print(f"  {rule}: {len(doc)} Step-2 default(s) in {DOCS[rule].name} (min {MIN_DOC_DEFAULTS[rule]}) — "
              f"{'MISMATCH' if (unknown or mism or short) else 'OK'} vs rules.yaml")

    if fails:
        print(f"\nFAIL — live screener and rules.yaml have drifted ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print("PASS: methodology parity — live JS (W1/W2) + command-doc Step-2 defaults (W1/W2/W3) == rules.yaml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
