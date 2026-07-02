"""Self-test for the sequential-lifecycle layer (runnable gate; exits non-zero on failure).

    python -m research.backtest.selftest_lifecycle
"""
from __future__ import annotations
from datetime import date

from .lifecycle import link_stages
from .robust import prob_greater

FAILS = []


def check(c, m):
    if not c:
        FAILS.append(m)


def main() -> int:
    K = 100

    # --- linkage causality + window ---
    # name A: TASI-W1 at 10; TASI-W2 at 50 (within K of TASI-W1 -> linked); TASI-W3 at 120 (within K of the TASI-W2 at 50 -> chain)
    # name B: TASI-W2 at 30 with NO prior TASI-W1 -> must NOT link (causality); TASI-W1 only at 200 (after) doesn't count
    # name C: TASI-W1 at 0; TASI-W2 at 500 (gap 500 > K -> NOT linked); so its TASI-W3 at 510 also cannot chain
    p1 = {"A": [10], "B": [200], "C": [0]}
    p2 = {"A": [50], "B": [30], "C": [500]}
    p3 = {"A": [120], "B": [], "C": [510]}
    L = link_stages(p1, p2, p3, K)

    check(L["w1"] == {("A", 10), ("B", 200), ("C", 0)}, f"w1 set wrong: {L['w1']}")
    check(("A", 50) in L["w2"], "A's TASI-W2@50 should link to TASI-W1@10")
    check(("B", 30) not in L["w2"], "B's TASI-W2@30 must NOT link (no prior TASI-W1 — causality)")
    check(("C", 500) not in L["w2"], "C's TASI-W2@500 must NOT link (gap > K)")
    check(L["w2"] == {("A", 50)}, f"w2 set should be exactly A@50: {L['w2']}")
    check(("A", 120) in L["w3"], "A's TASI-W3@120 should chain off the linked TASI-W2@50")
    check(("C", 510) not in L["w3"], "C's TASI-W3 cannot chain (its TASI-W2 never linked)")
    check(L["w3"] == {("A", 120)}, f"w3 set should be exactly A@120: {L['w3']}")

    # --- diagnostic confirmation (uses future) ---
    check(("A", 10) in L["w1_conf2"], "A's TASI-W1@10 confirms TASI-W2 (TASI-W2@50 within K ahead)")
    check(("A", 10) in L["w1_conf3"], "A's TASI-W1@10 confirms TASI-W3 (chain reaches TASI-W3@120)")
    check(("C", 0) not in L["w1_conf2"], "C's TASI-W1@0 does NOT confirm TASI-W2 (TASI-W2 is 500 away > K)")
    check(("B", 200) not in L["w1_conf2"], "B's TASI-W1@200 has no later TASI-W2 -> not confirmed")

    # --- window edge: exactly K apart links; K+1 does not ---
    e = link_stages({"X": [0]}, {"X": [K, K + 1]}, {"X": []}, K)
    check(("X", K) in e["w2"], "TASI-W2 exactly K after TASI-W1 should link (inclusive)")
    check(("X", K + 1) not in e["w2"], "TASI-W2 at K+1 after TASI-W1 must not link")

    # --- determinism ---
    check(link_stages(p1, p2, p3, K) == L, "link_stages must be deterministic")

    # --- prob_greater sanity (independent block bootstrap of two unpaired samples) ---
    dts = [date(2010, (i % 12) + 1, 1) for i in range(120)]
    hi = prob_greater(dts, [5.0] * 120, dts, [1.0] * 120, n_boot=1000, seed=0)   # B dominates A
    lo = prob_greater(dts, [1.0] * 120, dts, [5.0] * 120, n_boot=1000, seed=0)   # A dominates B
    sym = prob_greater(dts, [1.0, -1.0] * 60, dts, [1.0, -1.0] * 60, n_boot=2000, seed=0)  # equal
    check(hi is not None and hi > 0.99, f"prob_greater(B>>A) should be ~1, got {hi}")
    check(lo is not None and lo < 0.01, f"prob_greater(B<<A) should be ~0, got {lo}")
    check(0.3 < sym < 0.7, f"prob_greater(equal) should be ~0.5, got {sym}")
    check(prob_greater([], [], dts, [1.0] * 120) is None, "empty sample -> None")

    if FAILS:
        print(f"FAIL ({len(FAILS)}):")
        for f in FAILS:
            print("  -", f)
        return 1
    print("PASS: lifecycle self-test OK (linkage causality/window/chain + diagnostic + prob_greater).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
