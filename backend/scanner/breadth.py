"""Market breadth — a leading gauge of the momentum *environment*.

Breadth (how many stocks participate) diverges BEFORE the index at major turns:
when fewer names hold above their moving averages while the index still grinds up,
the advance is narrowing — a leading warning for a momentum trader to cut size.
This is the "should I be aggressive right now?" dial.

Computed over a ~100-name large-cap S&P sample (fast, representative), cached 6h.
Data flows through the same fetcher as everything else (CBOE/Alpaca/yfinance).
"""
from __future__ import annotations

import logging
import time

from .fetcher import fetch_ohlcv, SP500_SAMPLE

logger = logging.getLogger(__name__)

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 6 * 3600  # 6 hours


def get_breadth() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _compute() -> dict | None:
    total = a50 = a200 = nh = nl = up = down = 0
    for sym in SP500_SAMPLE:
        df = fetch_ohlcv(sym, period_days=400)
        if df is None or len(df) < 60:
            continue
        c, h, l = df["close"], df["high"], df["low"]
        price = float(c.iloc[-1])
        total += 1
        if price > float(c.rolling(50).mean().iloc[-1]):
            a50 += 1
        if len(c) >= 200 and price > float(c.rolling(200).mean().iloc[-1]):
            a200 += 1
        win = min(len(df), 252)
        if price >= float(h.iloc[-win:].max()) * 0.99:
            nh += 1
        if price <= float(l.iloc[-win:].min()) * 1.01:
            nl += 1
        if len(c) >= 2:
            prev = float(c.iloc[-2])
            if price > prev:
                up += 1
            elif price < prev:
                down += 1
    if total < 20:
        return None

    pct50 = round(a50 / total * 100, 1)
    pct200 = round(a200 / total * 100, 1)
    nhnl = nh - nl
    ad = up - down
    score = round((pct50 + pct200) / 2, 1)

    state = ("strong" if score >= 65 else "healthy" if score >= 50
             else "mixed" if score >= 40 else "weak" if score >= 30 else "risk-off")

    # SPY context → narrowing/divergence check (index high but breadth thin = leading caution).
    spy = fetch_ohlcv("SPY", period_days=300)
    spy_near_high = False
    if spy is not None and len(spy) >= 60:
        sp_price = float(spy["close"].iloc[-1])
        sp_hi = float(spy["high"].iloc[-min(len(spy), 252):].max())
        spy_near_high = sp_price >= sp_hi * 0.98
    divergent = bool(spy_near_high and pct200 < 50)

    pts = []
    pts.append({"label": "Participation", "detail":
        f"{pct50}% of large caps are above their 50-day MA and {pct200}% above their 200-day "
        f"(across {total} names). Above ~60% = broad participation; below ~40% = a narrow, fragile tape."})
    pts.append({"label": "New highs vs lows", "detail":
        f"{nh} names at/near 52-week highs vs {nl} at lows (net {nhnl:+}). "
        + ("Expanding new highs confirm the uptrend." if nhnl > 0
           else "Expanding new lows are a risk-off tell." if nhnl < 0 else "Balanced — no thrust either way.")})
    pts.append({"label": "Advance/decline (today)", "detail":
        f"{up} up vs {down} down today (net {ad:+}) — the day's participation tilt."})
    if divergent:
        pts.append({"label": "⚠ Divergence", "detail":
            f"SPY is near its 52-week high but only {pct200}% of stocks are above their 200-day MA — a "
            "narrowing, divergent advance. Fewer names are carrying the index, which historically precedes "
            "tops. For a momentum trader: tighten stops and trade only the strongest leaders."})
    pts.append({"label": "Bottom line", "detail":
        {"strong":  "Broad, healthy breadth — a green light to be aggressive with new momentum entries.",
         "healthy": "Healthy participation — a constructive environment for new entries, normal size.",
         "mixed":   "Mixed breadth — be selective; favour only A-grade setups and trim size.",
         "weak":    "Weak breadth — the tape is thinning; new breakouts fail more often, so reduce size and exposure.",
         "risk-off":"Risk-off breadth — most stocks below their 50-DMA; stand mostly aside until participation recovers.",
         }[state]})

    return {
        "pct_above_50dma":  pct50,
        "pct_above_200dma": pct200,
        "new_highs":        nh,
        "new_lows":         nl,
        "net_highs_lows":   nhnl,
        "advancers":        up,
        "decliners":        down,
        "net_advancers":    ad,
        "universe_size":    total,
        "breadth_score":    score,
        "state":            state,
        "divergent":        divergent,
        "interpretation_points": pts,
    }
