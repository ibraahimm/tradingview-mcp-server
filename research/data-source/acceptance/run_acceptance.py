#!/usr/bin/env python3
"""Run the vendor acceptance harness over a sample directory and print a scorecard.

    python research/data-source/acceptance/run_acceptance.py <sample_dir>

Exit 0 = every MUST passed; non-zero = at least one MUST failed (vendor rejected on this sample).
PARTIAL checks are reported but do not gate (they require human follow-up — see WORKFLOW.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # allow `import checks` when run as a script
from checks import evaluate  # noqa: E402


def main(argv) -> int:
    if len(argv) != 1:
        print("usage: run_acceptance.py <sample_dir>")
        return 2
    sample_dir = argv[0]
    res = evaluate(sample_dir)
    print(f"Vendor acceptance — sample: {sample_dir}\n")
    print(f"{'req':<4} {'tier':<8} {'result':<7} requirement / detail")
    print("-" * 88)
    must_failed = []
    for rid, r in res.items():
        mark = "PASS" if r["passed"] else "FAIL"
        if r["tier"] == "MUST" and not r["passed"]:
            must_failed.append(rid)
        print(f"{rid:<4} {r['tier']:<8} {mark:<7} {r['label']} — {r['detail']}")
    print("-" * 88)
    if must_failed:
        print(f"RESULT: REJECT — MUST failures: {', '.join(must_failed)}")
        return 1
    print("RESULT: all MUST passed on this sample. (Confirm PARTIAL R5/R7 + license R10 with a human.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
