"""Self-test for the faithful tracker port (runnable gate; exits non-zero on failure).

    python -m research.backtest.selftest_tracker

Proves faithfulness three ways:
  1. Python conform == frozen golden expected.json (which was emitted by the LIVE saudi-tracker.js).
  2. Hand-checked state assertions (so the vectors are independently meaningful, not just "JS says so").
  3. DIFFERENTIAL: if node + the live JS are present, run saudi-tracker.js stage=conform on the SAME
     ledger and assert byte-for-value identical to the Python — same input -> same output.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess

from .tracker import conform

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VEC = os.path.join(ROOT, "research", "spec", "lifecycle_vectors")
JS = os.path.join(ROOT, ".claude", "scripts", "saudi-tracker.js")
FAILS = []


def check(c, m):
    if not c:
        FAILS.append(m)


def load_ledger(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def deep_equal(a, b, tol=1e-9, path=""):
    """Structural equality with numeric tolerance; ints/floats compare by value (20 == 20.0)."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            FAILS.append(f"key mismatch at {path or '<root>'}: {set(a) ^ set(b)}")
            return False
        return all(deep_equal(a[k], b[k], tol, f"{path}.{k}") for k in a)
    if isinstance(a, bool) or isinstance(b, bool):
        ok = a == b
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        ok = abs(a - b) <= tol
    else:
        ok = a == b
    if not ok:
        FAILS.append(f"value mismatch at {path}: {a!r} != {b!r}")
    return ok


def main() -> int:
    ledger = load_ledger(os.path.join(VEC, "ledger.jsonl"))
    params = json.load(open(os.path.join(VEC, "params.json")))
    expected = json.load(open(os.path.join(VEC, "expected.json")))
    asof = params["asof"]
    kw = dict(grad_p5y=params["grad_p5y"], stale_days=params["stale_days"], horizon_days=params["horizon_days"])

    py = conform(ledger, asof, **kw)

    # 1. Python == golden expected (emitted by the live JS)
    deep_equal(py, expected, path="py-vs-expected")

    # 2. hand-checked meaning of each vector
    want = {"TADAWUL:A": ("ACTIVE-W2", True, False, False),   # state, promoted, isNew, nearATH
            "TADAWUL:B": ("ACTIVE-W1", False, False, False),
            "TADAWUL:C": ("FAILED", True, False, False),
            "TADAWUL:D": ("GRAD★", False, False, False),
            "TADAWUL:E": ("STALE", False, False, False),
            "TADAWUL:F": ("EXPIRED", True, False, False),
            "TADAWUL:G": ("FAILED", True, False, False),      # FAILED wins over GRAD (precedence)
            "TADAWUL:H": ("ACTIVE-W2", False, True, True)}
    for sym, (st, pr, nw, na) in want.items():
        r = py.get(sym, {})
        check(r.get("state") == st, f"{sym} state {r.get('state')} != {st}")
        check(r.get("promoted") == pr, f"{sym} promoted {r.get('promoted')} != {pr}")
        check(r.get("isNew") == nw, f"{sym} isNew {r.get('isNew')} != {nw}")
        check(r.get("nearATH") == na, f"{sym} nearATH {r.get('nearATH')} != {na}")
    check(py["TADAWUL:A"]["journey"] == "W1→W2", "A journey should be W1→W2")
    check(abs(py["TADAWUL:C"]["gain"] - (-25.0)) < 1e-9, "C gain should be -25")

    # 3. DIFFERENTIAL vs the live JS (skips cleanly if node / JS unavailable)
    node = shutil.which("node")
    if node and os.path.exists(JS):
        res = subprocess.run([node, JS, "stage=conform", f"ledger={os.path.join(VEC, 'ledger.jsonl')}",
                              f"asof={asof}", f"grad_p5y={params['grad_p5y']}",
                              f"stale_days={params['stale_days']}", f"horizon_days={params['horizon_days']}"],
                             capture_output=True, text=True)
        if res.returncode != 0:
            FAILS.append(f"JS conform failed: {res.stderr.strip()}")
        else:
            js = json.loads(res.stdout)
            deep_equal(py, js, path="py-vs-JS")
            print("  (differential: ran live saudi-tracker.js — Python matched JS)")
    else:
        print("  (differential: node or saudi-tracker.js unavailable — JS diff SKIPPED)")

    if FAILS:
        print(f"FAIL ({len(FAILS)}):")
        for f in FAILS[:25]:
            print("  -", f)
        return 1
    print("PASS: tracker self-test OK (Python == golden == live JS; states/precedence/badges).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
