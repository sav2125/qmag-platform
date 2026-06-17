"""Risk Range + TRADE/TREND/TAIL — Hedgeye-style volatility-bounded levels.

Two ideas borrowed from Hedgeye's process, both computed purely from price/volatility
(so they work on every stock, no options chain or external feed needed):

  1. Risk Range — an immediate-term *probable* price band. Centre is a short mean,
     half-width comes from realised volatility scaled to the horizon. Momentum names
     ride the TOP of their range; the LOW end is the lower-risk pullback entry — which
     is exactly how Qullamaggie buys (pullback to the rising EMA).

  2. TRADE / TREND / TAIL — three trend durations, each with an explicit level you are
     bullish ABOVE / bearish BELOW. The actionable *line* is the value-add a plain
     MA-stack lacks: "intermediate trend breaks on a close below $X."
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# (name, human label, lookback window in trading days)
_DUR = [("TRADE", "~3 weeks", 21), ("TREND", "~3 months", 63), ("TAIL", "~1 year", 200)]


def _slope_state(series: pd.Series, short: int = 5, band: float = 0.0015) -> str:
    s = series.dropna()
    n = len(s)
    if n < short + 3:
        return "flat"
    last, base = float(s.iloc[-1]), float(s.iloc[-1 - short])
    if base == 0:
        return "flat"
    slope = last / base - 1.0
    curl_up = last > float(s.iloc[-2]) > float(s.iloc[-3])
    if slope > band:
        return "rising"
    if slope < -band:
        return "turning_up" if curl_up else "falling"
    return "turning_up" if curl_up else "flat"


def compute_risk_range(df: pd.DataFrame, horizon: int = 10, z: float = 1.0) -> dict | None:
    if df is None or len(df) < 30:
        return None
    close = df["close"].astype(float)
    price = float(close.iloc[-1])

    rets = np.log(close / close.shift(1)).dropna()
    sigma_d = float(rets.tail(30).std())        # ~30d realised daily vol
    if not np.isfinite(sigma_d) or sigma_d <= 0:
        return None

    move = z * sigma_d * np.sqrt(horizon)        # fractional half-width over the immediate term
    center = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    low, high = center * (1 - move), center * (1 + move)
    pos = (price - low) / (high - low) * 100 if high > low else 50.0
    immediate = {
        "low": round(low, 2), "high": round(high, 2), "center": round(center, 2),
        "position_pct": round(pos, 0),
        "width_pct": round(move * 200, 1),       # full band as % of centre
        "horizon_days": horizon,
    }

    durations, bull, counted = [], 0, 0
    for name, label, win in _DUR:
        if len(close) <= win:
            durations.append({"name": name, "label": label, "level": None,
                              "above": None, "slope": None, "insufficient": True})
            continue
        lvl_series = close.rolling(win).mean()
        level = float(lvl_series.iloc[-1])
        above = price > level
        bull += 1 if above else 0
        counted += 1
        durations.append({"name": name, "label": label, "level": round(level, 2),
                          "above": above, "slope": _slope_state(lvl_series)})

    if counted == 0:
        return None
    trade = next((d for d in durations if d["name"] == "TRADE" and d["level"] is not None), None)
    trend = next((d for d in durations if d["name"] == "TREND" and d["level"] is not None), None)
    if bull == counted:
        ttt = "bullish_all"
    elif bull == 0:
        ttt = "bearish_all"
    elif trade and not trade["above"]:
        ttt = "rolling_over"          # lost the immediate-term line
    elif trade and trend and trade["above"] and trend["above"]:
        ttt = "bullish_trade_trend"
    else:
        ttt = "mixed"

    out = {"price": round(price, 2), "immediate": immediate,
           "durations": durations, "ttt_state": ttt}
    out["interpretation_points"] = _interpret(out)
    return out


_TTT_WORD = {
    "bullish_all": "Bullish across TRADE, TREND and TAIL — uptrend intact on every duration.",
    "bullish_trade_trend": "Bullish on TRADE + TREND (immediate & intermediate up); the long-term TAIL line is the remaining hurdle.",
    "mixed": "Mixed across durations — the trend is not aligned; be selective.",
    "rolling_over": "Lost the immediate-term (TRADE) line — momentum is rolling over short-term even if longer trends hold.",
    "bearish_all": "Bearish across all durations — downtrend; new longs are fighting the tape.",
}


def _interpret(o: dict) -> list[dict]:
    im = o["immediate"]
    pos = im["position_pct"]
    price = o["price"]
    pts = []

    if pos <= 25:
        zone = (f"Price ${price} sits near the LOW end ({pos:.0f}% of range) — this is the lower-risk "
                "pullback/buy zone if the trend is intact.")
    elif pos >= 85:
        zone = (f"Price ${price} is near/above the TOP ({pos:.0f}% of range) — extended; better to wait for a "
                "pullback toward the low end or trim into strength.")
    else:
        zone = f"Price ${price} sits mid-range ({pos:.0f}%) — no edge from the range alone here."
    pts.append({"label": "Risk Range", "detail":
        f"Immediate-term probable range ${im['low']}–${im['high']} (±{im['width_pct']/2:.1f}% around the "
        f"{im['horizon_days']}-day mean). {zone}"})

    pts.append({"label": "Duration trend", "detail": _TTT_WORD.get(o["ttt_state"], "")})

    lvls = [f"{d['name']} ${d['level']}" for d in o["durations"] if d.get("level") is not None]
    if lvls:
        pts.append({"label": "Key lines", "detail":
            "Bullish above / bearish below: " + ", ".join(lvls) +
            ". These are the levels that flip each duration's trend."})

    trend = next((d for d in o["durations"] if d["name"] == "TREND" and d.get("level") is not None), None)
    if trend and trend["above"]:
        bottom = (f"While the intermediate TREND line (${trend['level']}) holds, pullbacks toward "
                  f"${im['low']} are the lower-risk entries; a close below ${trend['level']} breaks the trend.")
    elif trend:
        bottom = (f"Below the intermediate TREND line (${trend['level']}) the intermediate trend is broken — "
                  "rallies into resistance are suspect until price reclaims it.")
    else:
        bottom = "Not enough history for the full duration ladder; rely on the range and shorter durations."
    pts.append({"label": "Bottom line", "detail": bottom})
    return pts
