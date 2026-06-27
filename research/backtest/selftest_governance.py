"""Self-test for research governance (runnable gate; exits non-zero on failure).

Hand-computed: time split, summary stats (mean/std/t/p), Bonferroni deflation, walk-forward
per-window OOS aggregates, and select_best_oos (selects on TRAIN, reports held-out TEST,
deflates by trials — and deliberately does NOT pick the config that only looks best on test).

    python -m research.backtest.selftest_governance
"""
from __future__ import annotations
from datetime import date

import polars as pl

from .governance import time_split, summary_stats, bonferroni, walk_forward, select_best_oos

FAILS: list[str] = []


def check(c, m):
    if not c:
        FAILS.append(m)


def approx(a, b, tol=1e-4):
    return a is not None and abs(a - b) < tol


def _frame(fwd):
    return pl.DataFrame({
        "date": [date(2021, 1, i + 1) for i in range(len(fwd))],
        "fwd_2": [float(v) for v in fwd],
        "passed": [True] * len(fwd),
    }).with_columns(pl.col("date").cast(pl.Date))


def main() -> int:
    lab = _frame([10, -5, 20, -10, 30, -15, 5, -5, 15, -25])  # d1..d10

    # 1. time_split is by date, test strictly after cutoff
    tr, te = time_split(lab, date(2021, 1, 5))
    check(tr.height == 5 and te.height == 5, "time_split sizes wrong")
    check(te.get_column("date").min() == date(2021, 1, 6), "test must start after cutoff")

    # 2. summary_stats on the test window [-15,5,-5,15,-25]
    s = summary_stats([-15, 5, -5, 15, -25])
    check(s["n"] == 5 and approx(s["mean"], -5.0), "summary mean wrong")
    check(approx(s["std"], 15.811388, 1e-5), "summary std wrong")
    check(approx(s["t"], -0.707107, 1e-5), "summary t wrong")
    check(approx(s["p"], 0.479500, 1e-4), "summary p (z-approx) wrong")

    # 3. Bonferroni deflation
    check(approx(bonferroni(0.04, 10), 0.40), "bonferroni 0.04*10 wrong")
    check(approx(bonferroni(0.40, 5), 1.0), "bonferroni should cap at 1.0")

    # 4. walk-forward per-window OOS aggregates: cutoffs d3,d6,d10
    folds = walk_forward(lab, 2, [date(2021, 1, 3), date(2021, 1, 6), date(2021, 1, 10)])
    check(folds[0]["stats"]["n"] == 3 and approx(folds[0]["stats"]["mean"], 25 / 3), "fold1 wrong")
    check(folds[1]["stats"]["n"] == 3 and approx(folds[1]["stats"]["mean"], 5 / 3), "fold2 wrong")
    check(folds[2]["stats"]["n"] == 4 and approx(folds[2]["stats"]["mean"], -2.5), "fold3 wrong")

    # 5. select_best_oos: A has best TRAIN; B only looks good on TEST. Discipline must pick A
    #    (by train) and report A's held-out TEST — NOT chase B's test mean.
    configs = {
        "A": (_frame([20, 30, 10]), _frame([5, 15, -5])),    # train mean 20, test mean 5
        "B": (_frame([0, -10, 5]), _frame([40, 30, 50])),    # train mean -1.67, test mean 40
    }
    r = select_best_oos(configs, 2)
    check(r["best"] == "A", f"should select A by train mean, got {r['best']}")
    check(r["n_trials"] == 2, "n_trials should be 2")
    check(approx(r["train"]["mean"], 20.0), "reported train mean wrong")
    check(r["test"]["n"] == 3 and approx(r["test"]["mean"], 5.0), "should report A's held-out TEST (mean 5)")
    check(r["deflated_p"] is not None and r["deflated_p"] >= r["test"]["p"], "deflated_p must be >= raw test p")

    if FAILS:
        print(f"FAIL ({len(FAILS)} issue(s)):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: governance self-test OK (split / stats / bonferroni / walk-forward / select_best_oos).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
