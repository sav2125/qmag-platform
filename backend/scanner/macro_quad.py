"""Fundamental GIP Quad — GDP/CPI/IP rate-of-change from FRED (Hedgeye-style nowcast).

Hedgeye classifies the macro regime by the FIRST DIFFERENCE of YoY Growth and YoY
Inflation (is each accelerating or decelerating). We replicate that on free FRED data
(no key, datacenter-friendly):

  Growth — climate (quarterly)  = Real GDP YoY (GDPC1) accel/decel
  Growth — weather (monthly)    = Industrial Production YoY (INDPRO) accel/decel  [timelier proxy]
  Inflation — both              = Headline CPI YoY (CPIAUCSL) accel/decel

This is the DATA read — what the macro numbers say — the complement to the price-implied
Quad (what the tape is trading). When they diverge, the tape is pricing one regime while
the data turns toward another (Hedgeye's "bullish until it isn't"). It's based on the
latest RELEASED data (a trailing read), not a forward forecast like Hedgeye's proprietary
nowcast model. Cached 12h.
"""
from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
_FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

# Quad metadata (mirrors the GIP playbook)
_QUAD = {
    1: ("Goldilocks", "Growth ↑ · Inflation ↓"),
    2: ("Reflation", "Growth ↑ · Inflation ↑"),
    3: ("Stagflation", "Growth ↓ · Inflation ↑"),
    4: ("Deflation", "Growth ↓ · Inflation ↓"),
}

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 12 * 3600


def _fred(sid: str):
    """Fetch a FRED series as ascending [(date, value)], skipping missing '.' rows."""
    try:
        r = requests.get(_FRED.format(sid=sid), headers=_UA, timeout=20)
        if r.status_code != 200:
            return None
    except Exception:
        logger.exception("FRED fetch failed: %s", sid)
        return None
    rows = []
    for line in r.text.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2 or parts[-1] in (".", ""):
            continue
        try:
            rows.append((parts[0], float(parts[-1])))
        except ValueError:
            continue
    return rows or None


def _yoy(rows, periods: int):
    """Year-over-year % change series, ascending [(date, pct)]."""
    return [(rows[i][0], (rows[i][1] / rows[i - periods][1] - 1) * 100)
            for i in range(periods, len(rows)) if rows[i - periods][1]]


def _quad(g_up: bool, i_up: bool) -> int:
    if g_up and not i_up:
        return 1
    if g_up and i_up:
        return 2
    if not g_up and i_up:
        return 3
    return 4


def _nearest(rows_map, ascending_dates, target):
    """Value at the latest date <= target (rows_map: {date: val})."""
    if target in rows_map:
        return target, rows_map[target]
    best = None
    for d in ascending_dates:
        if d <= target:
            best = d
        else:
            break
    return (best, rows_map[best]) if best else (None, None)


def _classify(g_name, g_now, g_prev, g_date, i_now, i_prev, i_date):
    g_delta, i_delta = g_now - g_prev, i_now - i_prev
    quad = _quad(g_delta >= 0, i_delta >= 0)
    name, tag = _QUAD[quad]
    return {
        "quad": quad, "quad_name": name, "quad_tag": tag,
        "growth": "accelerating" if g_delta >= 0 else "decelerating",
        "growth_delta_bps": round(g_delta * 100),
        "growth_metric": g_name, "growth_yoy": round(g_now, 2), "growth_yoy_prev": round(g_prev, 2),
        "growth_date": g_date,
        "inflation": "accelerating" if i_delta >= 0 else "decelerating",
        "inflation_delta_bps": round(i_delta * 100),
        "cpi_yoy": round(i_now, 2), "cpi_yoy_prev": round(i_prev, 2),
        "cpi_date": i_date,
    }


def get_macro_quad() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _compute() -> dict | None:
    gdp = _fred("GDPC1")        # Real GDP, quarterly (SAAR level)
    cpi = _fred("CPIAUCSL")     # CPI all-urban, monthly index (SA)
    ip = _fred("INDPRO")        # Industrial production, monthly index (SA)
    if not gdp or not cpi:
        return None

    gdp_yoy = _yoy(gdp, 4)      # quarterly YoY
    cpi_yoy = _yoy(cpi, 12)     # monthly YoY
    ip_yoy = _yoy(ip, 12) if ip else []
    if len(gdp_yoy) < 2 or len(cpi_yoy) < 4:
        return None

    cpi_map = dict(cpi_yoy)
    cpi_dates = [d for d, _ in cpi_yoy]

    # Climate (quarterly): clean single-period read — GDP YoY q/q change, with CPI YoY
    # aligned to the SAME quarters (avoids mixing a stale GDP quarter with fresh CPI).
    quarterly = None
    gd_now, gd_prev = gdp_yoy[-1], gdp_yoy[-2]
    ci_d1, ci_now = _nearest(cpi_map, cpi_dates, gd_now[0])
    ci_d0, ci_prev = _nearest(cpi_map, cpi_dates, gd_prev[0])
    if ci_now is not None and ci_prev is not None:
        quarterly = _classify("Real GDP YoY", gd_now[1], gd_prev[1], gd_now[0], ci_now, ci_prev, ci_d1)

    # Weather (monthly): freshest monthly data — IP YoY + CPI YoY, 3-month change.
    monthly = None
    if len(ip_yoy) >= 4 and len(cpi_yoy) >= 4:
        monthly = _classify("Industrial Production YoY", ip_yoy[-1][1], ip_yoy[-4][1], ip_yoy[-1][0],
                            cpi_yoy[-1][1], cpi_yoy[-4][1], cpi_yoy[-1][0])

    if quarterly is None and monthly is None:
        return None
    aligned = bool(quarterly and monthly and quarterly["quad"] == monthly["quad"])
    out = {
        "as_of": cpi_yoy[-1][0],
        "quarterly": quarterly, "monthly": monthly, "aligned": aligned,
    }
    out["interpretation_points"] = _interpret(out)
    return out


def _interpret(o):
    q, m = o.get("quarterly"), o.get("monthly")
    pts = []
    if q:
        pts.append({"label": f"Climate — Quarterly Quad {q['quad']}: {q['quad_name']}", "detail":
            f"Real GDP YoY {q['growth']} ({q['growth_yoy_prev']}% → {q['growth_yoy']}%) and Headline CPI YoY "
            f"{q['inflation']} ({q['cpi_yoy_prev']}% → {q['cpi_yoy']}%) over the last quarter. The dominant data regime."})
    if m:
        pts.append({"label": f"Weather — Monthly Quad {m['quad']}: {m['quad_name']}", "detail":
            f"Industrial Production YoY {m['growth']} and CPI YoY {m['inflation']} over the last 3 months — the "
            "timelier monthly read."})
    if q and m:
        pts.append({"label": "Data alignment", "detail":
            (f"Both the quarterly and monthly data agree on Quad {q['quad']}." if o["aligned"]
             else f"Monthly data (Quad {m['quad']}) is leading the quarterly (Quad {q['quad']}) — the regime is turning.")})
    pts.append({"label": "What this is", "detail":
        "The DATA read (FRED GDP/CPI/IP rate-of-change), Hedgeye-style. Compare it with the price-implied Quad above: "
        "when the tape and the data disagree, the market is pricing one regime while the fundamentals turn toward another."})
    pts.append({"label": "Caveat", "detail":
        "Based on the latest released data (GDP lags ~1 quarter, CPI/IP ~2-6 weeks) — a trailing read, not a forward "
        "nowcast. It can lag a fast inflection."})
    return pts
