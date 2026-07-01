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

    if fails:
        print(f"\nFAIL — live screener and rules.yaml have drifted ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print("PASS: methodology parity — live saudi-stage2.js / saudi-wave2.js == rules.yaml on all W1/W2 gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
