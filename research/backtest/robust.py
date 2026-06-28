"""Robustness layer — net-of-cost returns + cluster/block-bootstrap inference.

The rigor-pass t-stats assume independent observations. They are NOT: signals cluster in time
(many names trigger together; their forward returns are cross-sectionally correlated), which
deflates the variance and INFLATES naive t. A block bootstrap by calendar month resamples whole
date-blocks with replacement — preserving same-date cross-sectional correlation and short-term
temporal correlation — giving an honest SE / CI / p-value. And transaction costs are subtracted so
"excess" is what a trader could actually keep.
"""
from __future__ import annotations
import random
import statistics
from collections import defaultdict


def net_of_cost(mean_pct: float, round_trip_bps: float) -> float:
    """Subtract a round-trip transaction cost (in basis points) from a mean return in PERCENT."""
    return mean_pct - round_trip_bps / 100.0


def block_bootstrap(dates, values, n_boot: int = 5000, seed: int = 0) -> dict:
    """Block bootstrap by (year, month): resample whole month-blocks with replacement and recompute
    the pooled mean. Returns {mean, boot_se, ci_low, ci_high, p_boot, n, n_blocks}.

    p_boot is a two-sided percentile p for H0: mean = 0 (how much of the bootstrap mass sits on the
    far side of zero). Block resampling keeps within-month cross-sectional + temporal correlation."""
    pairs = [(d, v) for d, v in zip(dates, values) if v is not None]
    if not pairs:
        return {"mean": None, "boot_se": None, "ci_low": None, "ci_high": None,
                "p_boot": None, "n": 0, "n_blocks": 0}
    blocks = defaultdict(lambda: [0.0, 0])
    for d, v in pairs:
        b = blocks[(d.year, d.month)]
        b[0] += v
        b[1] += 1
    bl = list(blocks.values())
    nb = len(bl)
    obs = sum(v for _, v in pairs) / len(pairs)
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        s = c = 0.0
        for _ in range(nb):
            blk = bl[rng.randrange(nb)]
            s += blk[0]
            c += blk[1]
        means.append(s / c)
    means.sort()
    frac_le = sum(1 for m in means if m <= 0) / n_boot
    return {
        "mean": obs,
        "boot_se": statistics.pstdev(means),
        "ci_low": means[int(0.025 * n_boot)],
        "ci_high": means[min(int(0.975 * n_boot), n_boot - 1)],
        "p_boot": min(1.0, 2 * min(frac_le, 1 - frac_le)),
        "n": len(pairs),
        "n_blocks": nb,
    }
