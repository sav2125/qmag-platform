"""Sector RS rotation — a leading "where is leadership?" gauge.

Money rotates into leading sectors before broad moves. For each of the 11 SPDR
sectors we measure relative strength vs SPY (3-month RS level) and whether that RS
is improving or fading (1-month RS minus 3-month RS), then classify into the four
RRG-style quadrants: Leading / Weakening / Improving / Lagging. Tells a momentum
trader which groups to hunt in. Cached 6h.
"""
from __future__ import annotations

import logging
import time
from datetime import date

import pandas as pd

from .fetcher import fetch_ohlcv

logger = logging.getLogger(__name__)

_SECTORS = [
    ("XLK", "Technology"), ("XLC", "Communication"), ("XLY", "Consumer Disc."),
    ("XLF", "Financials"), ("XLI", "Industrials"), ("XLV", "Health Care"),
    ("XLP", "Consumer Staples"), ("XLE", "Energy"), ("XLU", "Utilities"),
    ("XLB", "Materials"), ("XLRE", "Real Estate"),
]

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 6 * 3600


def get_sector_rotation() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _pct(rel, a: int, b: int):
    """Relative performance of the sector/SPY ratio between bar -b and bar -a (%)."""
    return float(rel.iloc[-a] / rel.iloc[-b] - 1) * 100


def _ret_n(close, n: int):
    """Simple % return over the last n trading bars."""
    return round(float(close.iloc[-1] / close.iloc[-1 - n] - 1) * 100, 1) if len(close) > n else None


def _ret_ytd(df):
    """% return year-to-date (from the first trading bar of the current calendar year)."""
    yr = df.index[-1].year
    ytd = df[df.index.year == yr]
    if len(ytd) < 2:
        return None
    return round(float(ytd["close"].iloc[-1] / ytd["close"].iloc[0] - 1) * 100, 1)


def _compute() -> dict | None:
    spy = fetch_ohlcv("SPY", period_days=400)
    if spy is None or len(spy) < 70:
        return None
    spx = spy["close"]
    # SPY horizons (for the relative-to-SPY columns)
    spy_h = {"d1": _ret_n(spx, 1), "w1": _ret_n(spx, 5), "m1": _ret_n(spx, 21),
             "m3": _ret_n(spx, 63), "ytd": _ret_ytd(spy)}

    def _rel(a, b):
        return round(a - b, 1) if (a is not None and b is not None) else None

    rows = []
    for sym, name in _SECTORS:
        df = fetch_ohlcv(sym, period_days=400)
        if df is None or len(df) < 70:
            continue
        c = df["close"]
        # Align sector and SPY on common dates, then form the relative-strength ratio.
        pair = pd.concat([c, spx], axis=1, join="inner").dropna()
        if len(pair) < 65:
            continue
        rel = pair.iloc[:, 0] / pair.iloc[:, 1]   # sector / SPY — RRG RS-ratio
        rs_strength = round(_pct(rel, 1, 63), 1)              # 3-mo relative perf (RS level)
        rs_recent = _pct(rel, 1, 21)                          # last month relative perf
        rs_prior = _pct(rel, 21, 42)                          # prior month relative perf
        rs_momentum = round(rs_recent - rs_prior, 1)          # RS acceleration (RRG momentum)
        if rs_strength >= 0 and rs_momentum >= 0:
            quad = "leading"
        elif rs_strength >= 0:
            quad = "weakening"
        elif rs_momentum >= 0:
            quad = "improving"
        else:
            quad = "lagging"

        # Multi-horizon performance — absolute and relative-to-SPY (Hedgeye sector tables)
        absr = {"d1": _ret_n(c, 1), "w1": _ret_n(c, 5), "m1": _ret_n(c, 21),
                "m3": _ret_n(c, 63), "ytd": _ret_ytd(df)}
        relr = {k: _rel(absr[k], spy_h[k]) for k in absr}

        rows.append({"symbol": sym, "name": name, "rs_strength": rs_strength,
                     "rs_momentum": rs_momentum, "quadrant": quad,
                     "abs": absr, "rel": relr})
    if len(rows) < 5:
        return None
    rows.sort(key=lambda r: -r["rs_strength"])

    def names(q):
        return [r["name"] for r in rows if r["quadrant"] == q]

    leading = names("leading")
    weakening = names("weakening")
    improving = names("improving")
    lagging = names("lagging")
    pts = []
    if leading:
        pts.append({"label": "Leading sectors", "detail":
            f"{', '.join(leading)} — strong relative strength AND still accelerating. This is where leadership "
            "is concentrated; hunt new long setups here first."})
    if weakening:
        pts.append({"label": "Weakening (leaders cooling)", "detail":
            f"{', '.join(weakening)} — still outperforming SPY but momentum is decelerating. Existing longs OK, "
            "but be selective on new entries; leadership may be rotating away."})
    if improving:
        pts.append({"label": "Improving (early rotation)", "detail":
            f"{', '.join(improving)} — RS still below SPY but turning up. Early rotation; watch for emerging "
            "leaders before they become consensus."})
    if lagging:
        pts.append({"label": "Lagging — avoid", "detail":
            f"{', '.join(lagging)} — weak RS and still fading. Breakouts here fail more often; avoid new longs."})
    top = rows[0]
    bot = rows[-1]
    pts.append({"label": "Bottom line", "detail":
        f"Strongest group: {top['name']} ({top['rs_strength']:+}% vs SPY, 3-mo); weakest: {bot['name']} "
        f"({bot['rs_strength']:+}%). Trade with the rotation — favour leaders, treat laggards' breakouts with suspicion."})

    return {"as_of": date.today().isoformat(), "sectors": rows, "interpretation_points": pts}
