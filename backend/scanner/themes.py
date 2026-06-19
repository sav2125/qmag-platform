"""Theme rotation — which investable THEMES are leading, and the names to focus on.

GICS sectors (sectors.py) miss the cross-cutting themes that actually drive a momentum
book — cybersecurity, agentic-AI software, AI infrastructure, the AI-power trade,
quantum, space, robotics, biotech. This module carries curated baskets for each
(seeded from the canonical thematic indices — CIBR, IGV/AIQ, SMH, BOTZ, QTUM, UFO,
GRID, XBI — plus the pure-plays those ETFs underweight), then:

  • scores each theme's relative strength vs SPY + RS acceleration → RRG quadrant
    (Leading / Improving / Weakening / Lagging)  → "when is the theme rotating",
  • ranks the constituents within each theme by relative strength  → "what to focus on".

A comprehensive universe in; the leaders in the leading themes out. Cached 6h.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from statistics import median

from .fetcher import fetch_ohlcv

logger = logging.getLogger(__name__)

# Curated baskets — liquid US-listed names, seeded from the named thematic indices.
THEMES = [
    {"key": "cyber", "name": "Cybersecurity", "source": "CIBR / BUG", "tickers": [
        "PANW", "CRWD", "FTNT", "ZS", "NET", "S", "OKTA", "TENB", "QLYS",
        "VRNS", "RPD", "CHKP", "GEN", "RBRK", "FROG", "DT", "AKAM", "FFIV", "BAH"]},
    {"key": "ai_software", "name": "Agentic AI / Software", "source": "IGV + agentic", "tickers": [
        "PLTR", "NOW", "CRM", "SNOW", "MDB", "DDOG", "AI", "GTLB", "PATH", "APP",
        "HUBS", "TEAM", "NICE", "PEGA", "BILL", "MNDY", "SOUN", "BBAI", "PCOR", "ESTC"]},
    {"key": "ai_infra", "name": "AI Infrastructure / Semis", "source": "SMH / SOXX", "tickers": [
        "NVDA", "AVGO", "AMD", "TSM", "MU", "MRVL", "ARM", "LRCX", "KLAC", "AMAT",
        "ASML", "CDNS", "SNPS", "TXN", "ADI", "NXPI", "MPWR", "MCHP", "ALAB", "ON",
        "TER", "VRT", "SMCI", "DELL", "ANET", "CRDO", "COHR", "LITE", "CIEN", "WDC"]},
    {"key": "robotics", "name": "Robotics & Automation", "source": "BOTZ / ROBO", "tickers": [
        "ISRG", "NVDA", "TSLA", "CGNX", "AUR", "AVAV", "JBTM", "SYM", "ROK", "EMR",
        "ZBRA", "PTC", "NDSN", "TRMB", "TER", "SERV", "OUST", "KTOS"]},
    {"key": "quantum", "name": "Quantum Computing", "source": "QTUM", "tickers": [
        "IONQ", "RGTI", "QBTS", "QUBT", "ARQQ", "LAES", "QMCO", "IBM", "GOOGL", "MSFT",
        "NVDA", "HON", "AMD", "INTC", "FORM", "TER", "LRCX"]},
    {"key": "space", "name": "Space & Defense Tech", "source": "UFO / ARKX", "tickers": [
        "RKLB", "ASTS", "LUNR", "RDW", "PL", "IRDM", "GSAT", "VOYG", "KTOS", "RCAT",
        "AVAV", "ACHR", "JOBY", "BA", "RTX", "LMT", "NOC", "LHX", "HII", "GD"]},
    {"key": "power", "name": "Power / Grid / Nuclear", "source": "GRID + IPPs/uranium", "tickers": [
        "VST", "CEG", "NRG", "TLN", "GEV", "ETN", "PWR", "NVT", "HUBB", "AGX",
        "BWXT", "CCJ", "LEU", "OKLO", "SMR", "NNE", "UEC", "DNN", "NEE", "CW", "POWL", "FLR"]},
    {"key": "biotech", "name": "Biotech / GLP-1", "source": "XBI / IBB + GLP-1", "tickers": [
        "LLY", "VRTX", "REGN", "GILD", "AMGN", "BIIB", "MRNA", "VKTX", "ALT", "NBIX",
        "EXEL", "RVMD", "ARWR", "CYTK", "MDGL", "KRYS", "RYTM", "NUVL", "BEAM", "TGTX",
        "PTCT", "NTRA", "TWST"]},
]

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 6 * 3600


def get_theme_rotation() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _ret(c, n):
    return float(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100 if len(c) > n else None


def _seg(c, a, b):
    return float(c.iloc[-a] / c.iloc[-b] - 1) * 100 if len(c) > b else None


def _ret_ytd(df):
    yr = df.index[-1].year
    ytd = df[df.index.year == yr]
    return float(ytd["close"].iloc[-1] / ytd["close"].iloc[0] - 1) * 100 if len(ytd) >= 2 else None


def _med(xs):
    xs = [x for x in xs if x is not None]
    return round(median(xs), 1) if xs else None


def _compute() -> dict | None:
    spy = fetch_ohlcv("SPY", period_days=400)
    if spy is None or len(spy) < 70:
        return None
    spx = spy["close"]
    spy_h = {"d1": _ret(spx, 1), "w1": _ret(spx, 5), "m1": _ret(spx, 21), "m3": _ret(spx, 63), "ytd": _ret_ytd(spy)}
    spy_recent, spy_prior = _ret(spx, 21), _seg(spx, 22, 43)

    metric_cache: dict = {}

    def metrics(sym):
        if sym in metric_cache:
            return metric_cache[sym]
        m = None
        df = fetch_ohlcv(sym, period_days=400)
        if df is not None and len(df) >= 65:
            c = df["close"]
            rel = {}
            for k, n in (("d1", 1), ("w1", 5), ("m1", 21), ("m3", 63)):
                r = _ret(c, n)
                rel[k] = round(r - spy_h[k], 1) if (r is not None and spy_h[k] is not None) else None
            ry = _ret_ytd(df)
            rel["ytd"] = round(ry - spy_h["ytd"], 1) if (ry is not None and spy_h["ytd"] is not None) else None
            recent, prior = _ret(c, 21), _seg(c, 22, 43)
            accel = None
            if None not in (recent, prior, spy_recent, spy_prior):
                accel = round((recent - spy_recent) - (prior - spy_prior), 1)
            m = {"rel": rel, "accel": accel}
        metric_cache[sym] = m
        return m

    themes = []
    for t in THEMES:
        rows = [(sym, metrics(sym)) for sym in t["tickers"]]
        rows = [(s, m) for s, m in rows if m and m["rel"].get("m3") is not None]
        if len(rows) < 5:
            continue
        rs_strength = _med([m["rel"]["m3"] for _, m in rows])
        rs_momentum = _med([m["accel"] for _, m in rows if m["accel"] is not None])
        rel_agg = {k: _med([m["rel"].get(k) for _, m in rows]) for k in ("d1", "w1", "m1", "m3", "ytd")}
        sm = rs_strength or 0
        mo = rs_momentum or 0
        quad = ("leading" if sm >= 0 and mo >= 0 else "weakening" if sm >= 0
                else "improving" if mo >= 0 else "lagging")
        leaders = sorted(rows, key=lambda r: -(r[1]["rel"].get("m3") or -999))[:6]
        leaders = [{"symbol": s, "rel_m3": m["rel"].get("m3"), "rel_m1": m["rel"].get("m1")} for s, m in leaders]
        themes.append({
            "key": t["key"], "name": t["name"], "source": t["source"], "count": len(rows),
            "rs_strength": rs_strength, "rs_momentum": rs_momentum, "quadrant": quad,
            "rel": rel_agg, "leaders": leaders,
        })
    if not themes:
        return None
    themes.sort(key=lambda x: -(x["rs_strength"] or -999))
    return {"as_of": spy.index[-1].date().isoformat(), "themes": themes,
            "interpretation_points": _interpret(themes)}


def _interpret(themes):
    def names(q):
        return [t["name"] for t in themes if t["quadrant"] == q]

    leading, improving, lagging = names("leading"), names("improving"), names("lagging")
    pts = []
    if leading:
        top = themes[0]
        names_str = ", ".join(f"{l['symbol']}" for l in top["leaders"][:4])
        pts.append({"label": "Leading themes", "detail":
            f"{', '.join(leading)} — outperforming SPY and still accelerating. Strongest is {top['name']} "
            f"({top['rs_strength']:+}% vs SPY, 3-mo); focus names: {names_str}."})
    if improving:
        imp = next(t for t in themes if t["quadrant"] == "improving")
        pts.append({"label": "Improving (early rotation)", "detail":
            f"{', '.join(improving)} — RS turning up from below; early rotation. Watch {imp['name']} leaders "
            f"({', '.join(l['symbol'] for l in imp['leaders'][:3])}) for emerging breakouts before consensus."})
    if lagging:
        pts.append({"label": "Lagging — avoid", "detail":
            f"{', '.join(lagging)} — weak RS and still fading; breakouts here fail more often."})
    pts.append({"label": "How to use it", "detail":
        "Hunt new longs in the Leading and emerging Improving themes, starting with each theme's top-RS names; "
        "treat Lagging-theme breakouts with suspicion. Pair with a stock's Regime Fit on its Analyze page."})
    return pts
