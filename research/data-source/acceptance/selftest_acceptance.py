#!/usr/bin/env python3
"""Self-test for the acceptance harness (runnable gate; exits non-zero on failure).

Proves the harness discriminates: the GOOD synthetic sample passes every MUST; BAD samples fail
the specific MUST they are designed to violate. Without this, a vacuous harness that passed
everything would look fine.

    python research/data-source/acceptance/selftest_acceptance.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from checks import evaluate  # noqa: E402

SAMPLES = HERE / "samples"
FAILS = []


def must_ids(res):
    return {rid for rid, r in res.items() if r["tier"] == "MUST"}


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


def main() -> int:
    # 1. GOOD sample: every MUST passes
    good = evaluate(SAMPLES / "good")
    for rid in must_ids(good):
        check(good[rid]["passed"], f"good sample should pass {rid}, failed: {good[rid]['detail']}")

    # 2. bad_survivorship: R1 must fail (no delisted, no 2006); R6 also fails (no delisted)
    surv = evaluate(SAMPLES / "bad_survivorship")
    check(not surv["R1"]["passed"], "bad_survivorship should FAIL R1")
    check(not surv["R6"]["passed"], "bad_survivorship should FAIL R6 (no delisted)")

    # 3. bad_unadjusted: R2 + R3 must fail; R1/R4/R6 still pass (isolates the adjustment failure)
    badu = evaluate(SAMPLES / "bad_unadjusted")
    check(not badu["R2"]["passed"], "bad_unadjusted should FAIL R2 (no unadjusted/adj_factor)")
    check(not badu["R3"]["passed"], "bad_unadjusted should FAIL R3 (no corporate actions)")
    check(badu["R1"]["passed"], "bad_unadjusted should still PASS R1 (delisted + 2006 present)")
    check(badu["R4"]["passed"], "bad_unadjusted should still PASS R4")
    check(badu["R6"]["passed"], "bad_unadjusted should still PASS R6")

    if FAILS:
        print(f"FAIL ({len(FAILS)} issue(s)):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: acceptance harness self-test OK (good passes all MUST; bad samples fail the right ones).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
