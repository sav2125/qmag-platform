"""Short-sale volume pressure — a free daily proxy for short positioning.

FINRA publishes a consolidated daily short-sale-volume file covering every listed
name (no key, datacenter-friendly → works on Render). For each symbol it reports
the share of the day's volume that was sold short.

This is NOT classic short interest (shares short / days-to-cover, which is bi-monthly
and not free in real time). Market-maker hedging means a "normal" baseline is ~45-50%,
so the absolute number alone is noisy. The LEADING tell is the deviation + trend read
together with price: sustained elevated short% while price holds/rises = squeeze fuel
(shorts pressing into strength); rising short% while price falls = bearish confirmation.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import requests

from .fetcher import fetch_ohlcv

logger = logging.getLogger(__name__)

_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{ymd}.txt"
_UA = {"User-Agent": "qmag-platform research siddharthaman@gmail.com"}
_DAYS = 10                       # trading-day lookback
_FILE_CACHE: dict = {"ts": 0.0, "data": None}   # shared across all symbols
_FILE_TTL = 12 * 3600
_SYM_CACHE: dict = {}            # symbol -> (ts, result)
_SYM_TTL = 12 * 3600


def _fetch_day(d: date):
    """Fetch + parse one daily Reg SHO file → (yyyymmdd, {symbol: (short, total)})."""
    ymd = d.strftime("%Y%m%d")
    try:
        r = requests.get(_URL.format(ymd=ymd), headers=_UA, timeout=15)
    except Exception:
        return None
    if r.status_code != 200 or not r.text.startswith("Date|"):
        return None
    m: dict[str, tuple[float, float]] = {}
    for line in r.text.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) < 5:
            continue
        try:
            short, total = float(parts[2]), float(parts[4])
        except ValueError:
            continue
        if total > 0:
            m[parts[1].upper()] = (short, total)
    return (ymd, m) if m else None


def _load_recent():
    now = time.time()
    if _FILE_CACHE["data"] is not None and now - _FILE_CACHE["ts"] < _FILE_TTL:
        return _FILE_CACHE["data"]
    today = date.today()
    candidates = [today - timedelta(days=i) for i in range(1, 25)]   # ~3wks back to net _DAYS files
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(_fetch_day, candidates))
    days = sorted([r for r in results if r], key=lambda x: x[0])[-_DAYS:]
    if days:
        _FILE_CACHE.update(ts=now, data=days)
    return days


def _price_change(symbol: str):
    """Recent price context so the short read is directional (squeeze vs confirmation)."""
    df = fetch_ohlcv(symbol, period_days=40)
    if df is None or len(df) < 6:
        return None, None
    c = df["close"]
    chg5 = round(float(c.iloc[-1] / c.iloc[-6] - 1) * 100, 1) if len(c) > 6 else None
    chg20 = round(float(c.iloc[-1] / c.iloc[-21] - 1) * 100, 1) if len(c) > 21 else None
    return chg5, chg20


def get_short_volume(symbol: str) -> dict | None:
    symbol = symbol.upper().strip()
    now = time.time()
    cached = _SYM_CACHE.get(symbol)
    if cached and now - cached[0] < _SYM_TTL:
        return cached[1]

    days = _load_recent()
    if not days:
        return None
    series = []
    for ymd, m in days:
        if symbol in m:
            short, total = m[symbol]
            series.append({"date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}", "short_pct": round(short / total * 100, 1)})
    if len(series) < 2:
        return None

    pcts = [s["short_pct"] for s in series]
    latest = pcts[-1]
    avg = round(sum(pcts) / len(pcts), 1)
    half = max(1, len(pcts) // 2)
    trend = round(sum(pcts[-half:]) / len(pcts[-half:]) - sum(pcts[:half]) / len(pcts[:half]), 1)

    if avg >= 60:
        level = "very_high"
    elif avg >= 53:
        level = "elevated"
    elif avg <= 40:
        level = "low"
    else:
        level = "normal"

    chg5, chg20 = _price_change(symbol)
    result = {
        "symbol": symbol,
        "latest_pct": latest,
        "avg_pct": avg,
        "trend": trend,          # recent-half avg − earlier-half avg (pp)
        "level": level,          # very_high / elevated / normal / low
        "days": len(series),
        "series": series,
        "price_chg_5d": chg5,
        "price_chg_20d": chg20,
        "interpretation_points": _interpret(level, latest, avg, trend, chg5, chg20),
    }
    _SYM_CACHE[symbol] = (now, result)
    return result


def _interpret(level, latest, avg, trend, chg5, chg20):
    pts = []
    lvl_word = {"very_high": "very high", "elevated": "elevated", "normal": "normal", "low": "low"}[level]
    pts.append({"label": "Short-volume level", "detail":
        f"~{avg}% of recent daily volume was sold short ({lvl_word}; latest {latest}%). Baseline for liquid "
        "names is ~45-50% because market-makers short to provide liquidity, so read the deviation, not the raw number."})
    if trend >= 1.5:
        pts.append({"label": "Trend", "detail": f"Short pressure is rising (+{trend}pp recent vs earlier half) — shorts are getting more active."})
    elif trend <= -1.5:
        pts.append({"label": "Trend", "detail": f"Short pressure is easing ({trend}pp) — shorts are stepping back, a potential tailwind."})
    else:
        pts.append({"label": "Trend", "detail": "Short pressure is roughly steady over the window."})

    up = (chg20 or 0) > 0
    heavy = level in ("elevated", "very_high")
    if heavy and up:
        pts.append({"label": "Squeeze setup", "detail":
            f"Elevated shorting into a stock that's UP {chg20}% over the month — shorts pressing into strength is "
            "classic squeeze fuel; a breakout can force covering and accelerate the move."})
    elif heavy and not up and chg20 is not None:
        pts.append({"label": "Bearish confirmation", "detail":
            f"Heavy shorting while price is DOWN {chg20}% over the month — shorts are on the right side; treat "
            "long setups with extra caution until short pressure eases."})
    elif level == "low":
        pts.append({"label": "Little short pressure", "detail":
            "Below-baseline shorting — limited squeeze fuel, but also no active short overhang fighting the trend."})

    if heavy and up:
        bottom = "Net: a squeeze-prone name — elevated shorts vs a rising price. Confirms a long bias on a clean breakout."
    elif heavy:
        bottom = "Net: real short overhang against a weak/flat price — a headwind for longs."
    else:
        bottom = "Net: short positioning is unremarkable — not a differentiator here."
    pts.append({"label": "Bottom line", "detail": bottom})
    return pts
