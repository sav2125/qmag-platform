"""Market Gamma — index dealer-gamma regime (SPY + QQQ) at a glance.

Surfaces the dealer gamma-exposure (GEX) of the index ETFs so you don't have to run
them through Analyze manually. Positive/long gamma = dealers dampen moves (calm, mean-
reverting, "buy the dip / sell the rip"); negative/short gamma = dealers amplify moves
(breakouts & breakdowns run). The zero-gamma flip is the level where it switches.
Reuses options.compute_options (CBOE chain); cached 15min.
"""
from __future__ import annotations

import logging
import time
from datetime import date

from .fetcher import fetch_ohlcv
from .options import compute_options

logger = logging.getLogger(__name__)

_INDICES = [("SPY", "S&P 500"), ("QQQ", "Nasdaq 100")]
_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 15 * 60


def get_market_gamma() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _compute() -> dict | None:
    rows = []
    for sym, name in _INDICES:
        df = fetch_ohlcv(sym, period_days=60)
        if df is None or df.empty:
            continue
        spot = float(df["close"].iloc[-1])
        try:
            o = compute_options(sym, spot)
        except Exception:
            o = None
        gex = (o or {}).get("gex")
        if not gex or gex.get("gex_musd") is None:
            continue
        flip = gex.get("flip")
        above_flip = (flip is not None) and (spot > flip)
        rows.append({
            "symbol": sym, "name": name, "spot": round(spot, 2),
            "gex_musd": gex.get("gex_musd"), "regime": gex.get("regime"),
            "flip": flip, "above_flip": above_flip,
            "call_wall": gex.get("call_wall"), "put_wall": gex.get("put_wall"),
            "source": (o or {}).get("source"),
        })
    if not rows:
        return None
    return {"as_of": date.today().isoformat(), "indices": rows,
            "interpretation_points": _interpret(rows)}


def _interpret(rows) -> list[dict]:
    pts = []
    # Plain-English primer first (the user asked for a simple explanation).
    pts.append({"label": "In plain English", "detail":
        "Dealers who sell options hedge in the index. POSITIVE (long) gamma = they sell rallies and buy dips, "
        "so the market stays calm and mean-reverting (buy-the-dip / sell-the-rip). NEGATIVE (short) gamma = they "
        "do the opposite, so moves get amplified — breakouts and breakdowns run. The flip is the level that switches it."})
    for r in rows:
        pos = r["regime"] == "positive"
        loc = "above" if r["above_flip"] else "below"
        if pos and r["above_flip"]:
            read = ("calm / mean-reverting — fade the extremes, breakouts need a CLOSE through the call wall "
                    "(wicks get sold), expect chop and pinning")
        elif not pos or not r["above_flip"]:
            read = ("accelerant — moves run; breakouts extend and selloffs get fast. Trend-follow, don't fade")
        else:
            read = "transitional — watch the flip"
        walls = []
        if r.get("call_wall"):
            walls.append(f"call wall ${r['call_wall']} (resistance)")
        if r.get("put_wall"):
            walls.append(f"put wall ${r['put_wall']} (support)")
        pts.append({"label": f"{r['name']} ({r['symbol']})", "detail":
            f"Dealers {'long' if pos else 'short'} gamma ({r['gex_musd']:+}M); spot ${r['spot']} is {loc} the "
            f"${r['flip']} flip → {read}." + (f" Pinned between {', '.join(walls)}." if walls else "")})
    pts.append({"label": "For your trading", "detail":
        "Positive-gamma index = single-stock breakouts fade more often (demand closes, not wicks); negative-gamma "
        "index = momentum runs, press breakouts. A flush below the index flip is when broad selloffs turn violent."})
    return pts
