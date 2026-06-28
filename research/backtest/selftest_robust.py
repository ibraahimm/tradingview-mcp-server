"""Self-test for the robustness layer (runnable gate; exits non-zero on failure).

    python -m research.backtest.selftest_robust
"""
from __future__ import annotations
from datetime import date

from .robust import net_of_cost, block_bootstrap

FAILS = []


def check(c, m):
    if not c:
        FAILS.append(m)


def approx(a, b, tol=1e-6):
    return a is not None and abs(a - b) < tol


def main() -> int:
    # net_of_cost: 0.62% gross minus 31 bps round-trip = 0.31%
    check(approx(net_of_cost(0.62, 31), 0.31), "net_of_cost 0.62 - 0.31 should be 0.31")

    # all-positive constant sample across months -> bootstrap mean = const, CI tight, p ~ 0
    dts = [date(2020, m, 1) for m in range(1, 13)] * 5
    pos = block_bootstrap(dts, [5.0] * len(dts), n_boot=2000, seed=1)
    check(approx(pos["mean"], 5.0) and approx(pos["boot_se"], 0.0, 1e-9), "constant sample bootstrap wrong")
    check(pos["p_boot"] == 0.0, f"all-positive p_boot should be 0, got {pos['p_boot']}")

    # symmetric-around-zero sample -> not significant (p_boot large)
    vals = [(-1.0 if i % 2 else 1.0) for i in range(120)]
    dts2 = [date(2020, (i % 12) + 1, 1) for i in range(120)]
    sym = block_bootstrap(dts2, vals, n_boot=2000, seed=2)
    check(abs(sym["mean"]) < 1e-9, "symmetric sample mean should be ~0")
    check(sym["p_boot"] > 0.3, f"symmetric sample should be non-significant, p_boot={sym['p_boot']}")

    # determinism: same seed -> identical
    a = block_bootstrap(dts2, vals, n_boot=1000, seed=7)
    b = block_bootstrap(dts2, vals, n_boot=1000, seed=7)
    check(a == b, "same seed must reproduce")

    if FAILS:
        print(f"FAIL ({len(FAILS)}):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: robustness self-test OK (net-of-cost + block bootstrap CI/p + determinism).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
