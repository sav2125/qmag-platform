"""Style-factor leadership — "what is the market paying for right now?"

Inspired by Hedgeye's Style Factor Performance table. For each factor we rank the
large-cap universe, form a High-quartile and a Low-quartile basket, and report the
High − Low return spread across horizons. A positive spread = that factor is "in
gear" over that horizon.

For a momentum trader the key reads are: is MOMENTUM working (trend-following has a
tailwind), is HIGH BETA leading (risk-on), and is HIGH SHORT-INTEREST leading
(squeeze regime). We compute only the factors derivable from free data —
Momentum, Beta, Volatility, and Short-Interest (FINRA short-volume proxy) — and
skip the fundamentals-gated ones (Sales/EPS growth, yield, debt). Cached 6h.
"""
from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd

from .fetcher import SP500_SAMPLE, fetch_ohlcv

logger = logging.getLogger(__name__)

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 6 * 3600
_HZ = ["d1", "w1", "m1", "m3", "ytd"]
_HZ_BARS = {"d1": 1, "w1": 5, "m1": 21, "m3": 63}


def get_factor_leadership() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _ret_n(c, n):
    return float(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100 if len(c) > n else None


def _ret_ytd(df):
    yr = df.index[-1].year
    ytd = df[df.index.year == yr]
    return float(ytd["close"].iloc[-1] / ytd["close"].iloc[0] - 1) * 100 if len(ytd) >= 2 else None


def _short_pct_map():
    """Average short-volume % per symbol from FINRA Reg SHO (already cached). Optional."""
    try:
        from .short_volume import _load_recent
        days = _load_recent()
    except Exception:
        return {}
    if not days:
        return {}
    acc: dict[str, list[float]] = {}
    for _ymd, m in days:
        for sym, (short, total) in m.items():
            if total > 0:
                acc.setdefault(sym, []).append(short / total * 100)
    return {s: sum(v) / len(v) for s, v in acc.items() if v}


def _compute() -> dict | None:
    spy = fetch_ohlcv("SPY", period_days=400)
    if spy is None or len(spy) < 130:
        return None
    spy_ret = np.log(spy["close"] / spy["close"].shift(1)).dropna()

    metrics: dict[str, dict] = {}     # sym -> {ret horizons, beta, vol, mom}
    for sym in SP500_SAMPLE:
        df = fetch_ohlcv(sym, period_days=400)
        if df is None or len(df) < 130:
            continue
        c = df["close"]
        rets = {h: _ret_n(c, _HZ_BARS[h]) for h in _HZ_BARS}
        rets["ytd"] = _ret_ytd(df)
        if any(rets[h] is None for h in ("m1", "m3")):
            continue
        # beta + realised vol from aligned daily returns
        r = np.log(c / c.shift(1)).dropna()
        pair = pd.concat([r, spy_ret], axis=1, join="inner").dropna().tail(120)
        beta = float(pair.iloc[:, 0].cov(pair.iloc[:, 1]) / pair.iloc[:, 1].var()) if len(pair) > 30 else None
        vol = float(r.tail(63).std() * np.sqrt(252) * 100) if len(r) > 63 else None
        mom = _ret_n(c, 126)          # 6-month momentum (ranking metric)
        metrics[sym] = {"ret": rets, "beta": beta, "vol": vol, "mom": mom}

    if len(metrics) < 20:
        return None

    short_map = _short_pct_map()
    for sym, m in metrics.items():
        m["short"] = short_map.get(sym)

    factor_defs = [
        ("Momentum", "mom", "High momentum", "Low momentum"),
        ("Beta", "beta", "High beta", "Low beta"),
        ("Volatility", "vol", "High volatility", "Low volatility"),
        ("Short Interest", "short", "High short %", "Low short %"),
    ]
    factors = []
    for label, key, hi_lbl, lo_lbl in factor_defs:
        ranked = sorted([s for s in metrics if metrics[s].get(key) is not None],
                        key=lambda s: metrics[s][key], reverse=True)
        if len(ranked) < 12:
            continue
        q = max(3, len(ranked) // 4)
        high, low = ranked[:q], ranked[-q:]
        spread = {}
        for h in _HZ:
            hv = [metrics[s]["ret"][h] for s in high if metrics[s]["ret"].get(h) is not None]
            lv = [metrics[s]["ret"][h] for s in low if metrics[s]["ret"].get(h) is not None]
            spread[h] = round(sum(hv) / len(hv) - sum(lv) / len(lv), 1) if hv and lv else None
        leader = "high" if (spread.get("m1") or 0) >= 0 else "low"
        factors.append({"factor": label, "high_label": hi_lbl, "low_label": lo_lbl,
                        "spread": spread, "leader": leader, "basket_size": q})

    if not factors:
        return None

    return {"as_of": spy.index[-1].date().isoformat(), "universe": len(metrics),
            "factors": factors, "interpretation_points": _interpret(factors)}


def _f(factors, name):
    return next((f for f in factors if f["factor"] == name), None)


def _interpret(factors):
    pts = []
    mom = _f(factors, "Momentum")
    beta = _f(factors, "Beta")
    si = _f(factors, "Short Interest")

    if mom and mom["spread"].get("m1") is not None:
        s = mom["spread"]["m1"]
        if s >= 1:
            pts.append({"label": "Momentum (in gear)", "detail":
                f"High-momentum names are beating low-momentum by +{s}% over the past month — trend-following is "
                "working, a tailwind for breakout/EP setups. This is the regime Qullamaggie setups need."})
        elif s <= -1:
            pts.append({"label": "Momentum (out of favor)", "detail":
                f"High-momentum names are LAGGING low-momentum by {s}% over the month — a mean-reversion / "
                "rotation regime where breakouts fail more often. Be selective and tighten risk."})
        else:
            pts.append({"label": "Momentum (neutral)", "detail":
                "Momentum factor is roughly flat — no strong tailwind or headwind for trend-following right now."})

    if beta and beta["spread"].get("m1") is not None:
        s = beta["spread"]["m1"]
        pts.append({"label": "Risk appetite (Beta)", "detail":
            (f"High-beta leading by +{s}% (1M) — risk-on; the market is rewarding aggression."
             if s >= 1 else
             f"Low-beta leading (high-beta {s}% behind, 1M) — defensive/risk-off; favor quality and reduce size."
             if s <= -1 else
             "Beta factor flat — no clear risk-on/risk-off tilt.")})

    if si and si["spread"].get("m1") is not None:
        s = si["spread"]["m1"]
        if s >= 1:
            pts.append({"label": "Squeeze regime (Short Interest)", "detail":
                f"Heavily-shorted names are OUTPERFORMING by +{s}% (1M) — a short-squeeze tailwind; crowded shorts "
                "are getting run over."})
        elif s <= -1:
            pts.append({"label": "Shorts winning (Short Interest)", "detail":
                f"Heavily-shorted names are LAGGING by {s}% (1M) — shorts are on the right side; high-SI longs are risky."})

    mom_on = mom and (mom["spread"].get("m1") or 0) >= 1
    beta_on = beta and (beta["spread"].get("m1") or 0) >= 1
    if mom_on and beta_on:
        bottom = "Aggressive regime: momentum + high beta both leading. Press winners, full size on A-setups."
    elif (mom and (mom["spread"].get("m1") or 0) <= -1) or (beta and (beta["spread"].get("m1") or 0) <= -1):
        bottom = "Defensive regime: momentum and/or beta out of favor. Smaller size, demand cleaner setups, expect more failed breakouts."
    else:
        bottom = "Mixed factor regime: no decisive risk-on/off lean — trade the individual setup on its own merits."
    pts.append({"label": "Bottom line", "detail": bottom})
    return pts
