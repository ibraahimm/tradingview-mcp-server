"""FUNCTIONS adapter — exposes the engine under the golden-vector runner contract
(../spec/conformance/runner_contract.md) so the SAME frozen vectors validate the real
engine, not just the reference implementation.

    python research/spec/conformance/reference_runner.py --adapter=research.engine.conformance:FUNCTIONS
"""
from __future__ import annotations
from . import functions as fx

FUNCTIONS = {
    "ema": fx.ema,
    "perf_calendar": fx.perf_calendar,
    "running_max": fx.running_max,
    "rolling_extreme": fx.rolling_extreme,
    "ratios": fx.ratios,
}
