"""Fibonacci retracement + extension levels, anchored to the dominant recent swing.

Powers the /analyze `fibonacci` field and the ta-expert agent's Fibonacci read.

The hard part of Fibonacci is the ANCHOR — garbage swing in, garbage levels out.
We anchor deterministically to the dominant swing inside a lookback window: the
absolute highest high and lowest low, ordered by time to infer the leg direction
(if the high prints AFTER the low, the active leg is up). That removes the #1
failure mode — arbitrary/forced anchoring — and makes the levels reproducible.

A Fibonacci level is only a *line on a screen* until something confirms it
(prior S/R, a moving average, a reversal candle). These levels are a confluence
map, not a standalone trigger — see the ta-expert agent's Fibonacci framework.
"""
from __future__ import annotations

import pandas as pd

# Retracement ratios (pullback levels). 0.5 is not a true Fibonacci ratio but is
# a key psychological level traders watch, so it is included by convention.
RETRACEMENT_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]
# Extension ratios — projected targets beyond the swing in the trend direction.
EXTENSION_RATIOS = [1.272, 1.618, 2.0, 2.618]
# Golden pocket — the high-probability reaction band between the 61.8% and 65%
# retracement, where retail, institutions and algos all cluster.
GOLDEN_POCKET = (0.618, 0.65)


def compute_fibonacci(df: pd.DataFrame, lookback: int = 120) -> dict | None:
    """Anchor a Fibonacci grid to the dominant swing in the last ``lookback`` bars.

    Returns a dict with the anchor swing (price + date), the retracement ladder,
    extension targets, the golden-pocket band, and where current price sits — or
    ``None`` if data is too short or the swing is degenerate.
    """
    if df is None or len(df) < 20:
        return None

    n = len(df)
    window = min(lookback, n)
    seg = df.iloc[n - window:]
    high = seg["high"]
    low = seg["low"]

    hi_px = float(high.max())
    lo_px = float(low.min())
    rng = hi_px - lo_px
    if rng <= 0:
        return None

    hi_pos = int(high.values.argmax())   # position of the high within the window
    lo_pos = int(low.values.argmin())    # position of the low within the window

    # Leg direction: whichever extreme printed LAST defines the active impulse.
    uptrend = hi_pos > lo_pos
    direction = "uptrend" if uptrend else "downtrend"

    swing_high_date = str(seg.index[hi_pos].date())
    swing_low_date = str(seg.index[lo_pos].date())
    price = float(df["close"].iloc[-1])

    def _retr(ratio: float) -> float:
        # Uptrend → pull back DOWN from the high; downtrend → pull back UP from the low.
        return round(hi_px - rng * ratio, 2) if uptrend else round(lo_px + rng * ratio, 2)

    def _ext(ratio: float) -> float:
        # Project beyond the swing in the trend direction (ratio > 1.0).
        return round(lo_px + rng * ratio, 2) if uptrend else round(hi_px - rng * ratio, 2)

    retracements = [{"ratio": r, "pct": round(r * 100, 1), "price": _retr(r)} for r in RETRACEMENT_RATIOS]
    extensions = [{"ratio": e, "pct": round(e * 100, 1), "price": _ext(e)} for e in EXTENSION_RATIOS]

    gp_a, gp_b = _retr(GOLDEN_POCKET[0]), _retr(GOLDEN_POCKET[1])
    gp_low, gp_high = sorted([gp_a, gp_b])
    in_golden_pocket = gp_low <= price <= gp_high

    # How far price has retraced the active leg (0% = at the leg's far extreme).
    depth = (hi_px - price) / rng if uptrend else (price - lo_px) / rng
    depth = round(max(0.0, min(depth, 1.5)) * 100, 1)

    # Nearest reference level to current price (swing extremes + retracement ladder).
    levels_for_nearest = [("swing low", lo_px), ("swing high", hi_px)] + \
                         [(f"{r['pct']:.1f}% retr", r["price"]) for r in retracements]
    nearest_name, nearest_px = min(levels_for_nearest, key=lambda kv: abs(kv[1] - price))

    return {
        "direction":         direction,
        "lookback_bars":     window,
        "swing_low":         round(lo_px, 2),
        "swing_high":        round(hi_px, 2),
        "swing_low_date":    swing_low_date,
        "swing_high_date":   swing_high_date,
        "range":             round(rng, 2),
        "retracements":      retracements,
        "extensions":        extensions,
        "golden_pocket":     {"low": gp_low, "high": gp_high},
        "in_golden_pocket":  in_golden_pocket,
        "retrace_depth_pct": depth,
        "nearest_level":     {"name": nearest_name, "price": round(nearest_px, 2)},
        "price":             round(price, 2),
    }
