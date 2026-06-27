"""Event-study backtest layer.

Labels per-bar signals (from the screen run) with forward return at a horizon, handling
delisting terminal values and right-censoring, then aggregates. This is the layer that answers
"does gate X improve forward return?" out-of-sample. See README.md.
"""
