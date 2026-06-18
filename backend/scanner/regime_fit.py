"""Regime fit — does this stock have the macro wind at its back?

Bridges the macro layer (Quad regime, sector rotation, style factors) down to a
single stock. A Qullamaggie setup in a leading sector, while the tape is in Quad 1/2
and momentum is in gear, has a tailwind; the same setup in a lagging sector during a
Quad 3/4 / momentum-out-of-favor regime is fighting the tape. Pure compute off the
already-cached macro modules + a ticker→sector map. Cheap; safe to call per stock.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta

import pandas as pd

from .fetcher import _http_client

logger = logging.getLogger(__name__)

_SP500_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies"
    "/main/data/constituents.csv"
)

_GICS_TO_ETF = {
    "Information Technology": ("XLK", "Technology"),
    "Health Care": ("XLV", "Health Care"),
    "Financials": ("XLF", "Financials"),
    "Consumer Discretionary": ("XLY", "Consumer Disc."),
    "Communication Services": ("XLC", "Communications"),
    "Industrials": ("XLI", "Industrials"),
    "Consumer Staples": ("XLP", "Consumer Staples"),
    "Energy": ("XLE", "Energy"),
    "Utilities": ("XLU", "Utilities"),
    "Real Estate": ("XLRE", "Real Estate"),
    "Materials": ("XLB", "Materials"),
}

_SECTOR_MAP: dict = {"ts": None, "map": {}}      # symbol -> GICS sector
_MAP_TTL = timedelta(hours=24)


def _sector_map() -> dict:
    now = datetime.utcnow()
    if _SECTOR_MAP["ts"] and now - _SECTOR_MAP["ts"] < _MAP_TTL and _SECTOR_MAP["map"]:
        return _SECTOR_MAP["map"]
    try:
        r = _http_client.get(_SP500_CSV_URL, follow_redirects=True)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        m = {}
        for _, row in df.iterrows():
            sym = str(row["Symbol"]).replace(".", "-").strip().upper()
            m[sym] = str(row["GICS Sector"]).strip()
        _SECTOR_MAP.update(ts=now, map=m)
    except Exception:
        logger.warning("regime_fit: sector map fetch failed", exc_info=True)
    return _SECTOR_MAP["map"]


def regime_fit(symbol: str) -> dict | None:
    """Return the stock's macro tailwind/headwind read, or None if macro unavailable."""
    from .sectors import get_sector_rotation
    from .regime import get_regime
    from .factors import get_factor_leadership

    symbol = symbol.upper().strip()
    sectors = get_sector_rotation()
    regime = get_regime()
    factors = get_factor_leadership()
    if sectors is None and regime is None:
        return None

    score, points = 0, []

    # ── Sector leadership ──────────────────────────────────────────────────────
    gics = _sector_map().get(symbol)
    sector_etf = sector_name = sector_quad = None
    sector_rs = None
    if gics and gics in _GICS_TO_ETF and sectors:
        sector_etf, sector_name = _GICS_TO_ETF[gics]
        row = next((r for r in sectors["sectors"] if r["symbol"] == sector_etf), None)
        if row:
            sector_quad = row["quadrant"]
            sector_rs = row["rs_strength"]
            if sector_quad in ("leading", "improving"):
                score += 1
                points.append({"label": "Sector — tailwind", "detail":
                    f"{sector_name} ({sector_etf}) is {sector_quad} ({sector_rs:+}% vs SPY, 3-mo) — money is "
                    "rotating into this group."})
            elif sector_quad == "lagging":
                score -= 1
                points.append({"label": "Sector — headwind", "detail":
                    f"{sector_name} ({sector_etf}) is lagging ({sector_rs:+}% vs SPY) — breakouts in weak sectors "
                    "fail more often."})
            else:
                points.append({"label": "Sector — neutral", "detail":
                    f"{sector_name} ({sector_etf}) is {sector_quad} ({sector_rs:+}% vs SPY) — leadership is fading."})
    elif not gics:
        points.append({"label": "Sector — not mapped", "detail":
            f"{symbol} isn't in the S&P 500 sector map, so sector leadership can't be scored."})

    # ── Tape Quad posture (use the weather / monthly read) ─────────────────────
    quad = quad_name = posture = None
    if regime and regime.get("monthly"):
        m = regime["monthly"]
        quad, quad_name = m["quad"], m["quad_name"]
        if quad in (1, 2):
            score += 1
            posture = "green light"
            points.append({"label": "Regime — green light", "detail":
                f"The tape is trading Quad {quad} ({quad_name}) — a pro-growth, momentum-friendly backdrop for new longs."})
        else:
            score -= 1
            posture = "defend"
            points.append({"label": "Regime — defend", "detail":
                f"The tape is trading Quad {quad} ({quad_name}) — defensive; breakouts are lower-probability, size down."})

    # ── Style-factor regime (momentum in gear?) ────────────────────────────────
    factor_on = None
    if factors:
        mom = next((f for f in factors["factors"] if f["factor"] == "Momentum"), None)
        if mom and mom["spread"].get("m1") is not None:
            s = mom["spread"]["m1"]
            factor_on = s >= 0
            if s >= 1:
                score += 1
                points.append({"label": "Factor — tailwind", "detail":
                    f"Momentum factor is in gear (+{s}% 1M) — trend-following / breakouts are being rewarded."})
            elif s <= -1:
                score -= 1
                points.append({"label": "Factor — headwind", "detail":
                    f"Momentum factor is out of favor ({s}% 1M) — a mean-reversion regime where breakouts fail more."})

    verdict = "tailwind" if score >= 2 else "headwind" if score < 0 else "neutral"
    bottom = {
        "tailwind": "Net: the macro wind is at this setup's back — favourable for a full-conviction entry.",
        "neutral": "Net: mixed macro backdrop — let the setup and price action carry the decision.",
        "headwind": "Net: this setup is fighting the tape — demand an A+ setup, size down, or wait for the regime to turn.",
    }[verdict]
    points.append({"label": "Bottom line", "detail": bottom})

    return {
        "symbol": symbol,
        "verdict": verdict, "score": score,
        "sector": sector_name, "sector_etf": sector_etf,
        "sector_quadrant": sector_quad, "sector_rs": sector_rs,
        "quad": quad, "quad_name": quad_name, "posture": posture,
        "momentum_on": factor_on,
        "interpretation_points": points,
    }
