"""Market-Implied Quad — a Growth/Inflation regime read inferred from price action.

Hedgeye's GIP "Quads" classify the macro regime by the *rate of change* of Growth
and Inflation (Quad 1 Goldilocks, 2 Reflation, 3 Stagflation, 4 Deflation), each
with a distinct asset/sector/factor playbook. Their real model nowcasts GDP & CPI —
which we can't do on free data. Instead we infer the Quad the MARKET is *trading*
from cross-asset behaviour we already compute: sector leadership, style factors,
credit and breadth. It's a heuristic mirror, not the macro nowcast — but it ties the
whole platform's context layer into one actionable regime + playbook. Cached 6h.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 6 * 3600

# Hedgeye GIP playbook (condensed from the Quad expected-value table)
_PLAYBOOK = {
    1: {"name": "Goldilocks", "tag": "Growth ↑ · Inflation ↓",
        "best_sectors": ["Technology", "Consumer Disc.", "Communications", "Industrials", "Materials"],
        "best_factors": ["High Beta", "Momentum", "Secular Growth", "Small Caps"],
        "best_assets": ["Equities", "Credit", "Commodities"],
        "momentum_note": "Ideal for Qullamaggie — high-beta momentum is the leadership; press breakouts and run winners."},
    2: {"name": "Reflation", "tag": "Growth ↑ · Inflation ↑",
        "best_sectors": ["Technology", "Industrials", "Financials", "Energy", "Consumer Disc."],
        "best_factors": ["Secular Growth", "High Beta", "Small Caps", "Momentum"],
        "best_assets": ["Commodities", "Equities", "Credit"],
        "momentum_note": "Still pro-growth — momentum works; add inflation beneficiaries (Energy/Materials) to the hunt list."},
    3: {"name": "Stagflation", "tag": "Growth ↓ · Inflation ↑",
        "best_sectors": ["Utilities", "Energy", "REITs", "Consumer Staples", "Health Care"],
        "best_factors": ["Low Beta", "Quality", "Min Vol"],
        "best_assets": ["Gold", "Commodities", "Fixed Income"],
        "momentum_note": "Defensive — momentum breakouts fail more often. Favor low-beta/quality, trade smaller, demand cleaner setups."},
    4: {"name": "Deflation", "tag": "Growth ↓ · Inflation ↓",
        "best_sectors": ["Consumer Staples", "Health Care", "Utilities"],
        "best_factors": ["Low Beta", "Dividend Yield", "Quality", "Defensives"],
        "best_assets": ["Fixed Income", "Gold", "USD"],
        "momentum_note": "Risk-off — Qullamaggie longs struggle. Stand aside or minimal starter size until the regime turns."},
}

_CYCLICAL = ["XLK", "XLY", "XLI", "XLF", "XLC"]
_DEFENSIVE = ["XLP", "XLU", "XLV", "XLRE"]
_INFLATION = ["XLE", "XLB"]


def get_regime() -> dict | None:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = _compute()
    if data is not None:
        _CACHE.update(ts=now, data=data)
    return data


def _compute() -> dict | None:
    from .sectors import get_sector_rotation
    from .factors import get_factor_leadership
    from .breadth import get_breadth
    from .positioning import fetch_credit_spread

    sectors = get_sector_rotation()
    factors = get_factor_leadership()
    if sectors is None and factors is None:
        return None

    g_votes, i_votes, evidence = [], [], []

    def vote(axis, label, detail, v):
        (g_votes if axis == "growth" else i_votes).append(v)
        evidence.append({"axis": axis, "label": label, "detail": detail, "vote": v})

    # ── Growth axis ──────────────────────────────────────────────────────────
    if sectors:
        rs = {r["symbol"]: r["rs_strength"] for r in sectors["sectors"]}
        cyc = [rs[s] for s in _CYCLICAL if s in rs]
        def_ = [rs[s] for s in _DEFENSIVE if s in rs]
        if cyc and def_:
            tilt = sum(cyc) / len(cyc) - sum(def_) / len(def_)
            vote("growth", "Sector leadership",
                 f"Cyclicals {'leading' if tilt >= 0 else 'lagging'} defensives by {tilt:+.1f}pp (3-mo RS).",
                 1 if tilt >= 0 else -1)
    if factors:
        fmap = {f["factor"]: f for f in factors["factors"]}
        if "Beta" in fmap and fmap["Beta"]["spread"].get("m1") is not None:
            s = fmap["Beta"]["spread"]["m1"]
            vote("growth", "Risk appetite (Beta factor)",
                 f"High-beta {'leading' if s >= 0 else 'lagging'} low-beta by {s:+}% (1M).", 1 if s >= 0 else -1)
        if "Momentum" in fmap and fmap["Momentum"]["spread"].get("m1") is not None:
            s = fmap["Momentum"]["spread"]["m1"]
            vote("growth", "Momentum factor",
                 f"Momentum {'in gear' if s >= 0 else 'out of favor'} ({s:+}% 1M).", 1 if s >= 0 else -1)

    breadth = get_breadth()
    if breadth and breadth.get("breadth_score") is not None:
        bs = breadth["breadth_score"]
        vote("growth", "Market breadth",
             f"Breadth score {bs}/100 — participation {'healthy' if bs >= 50 else 'thin'}.", 1 if bs >= 50 else -1)

    try:
        credit = fetch_credit_spread()
    except Exception:
        credit = None
    if credit and credit.get("vote") is not None and credit["vote"] != 0:
        vote("growth", "Credit (HY OAS)",
             f"HY spreads {'tightening (risk-on)' if credit['vote'] > 0 else 'widening (risk-off)'} at {credit.get('oas')}%.",
             1 if credit["vote"] > 0 else -1)

    # ── Inflation axis ───────────────────────────────────────────────────────
    if sectors:
        infl = [rs[s] for s in _INFLATION if s in rs]
        if infl:
            avg = sum(infl) / len(infl)
            vote("inflation", "Energy/Materials leadership",
                 f"Energy + Materials {'leading' if avg >= 0 else 'lagging'} the market ({avg:+.1f}pp 3-mo RS).",
                 1 if avg >= 0 else -1)
            # Energy vs Tech: real-asset vs growth tilt
            if "XLE" in rs and "XLK" in rs:
                d = rs["XLE"] - rs["XLK"]
                vote("inflation", "Real assets vs growth",
                     f"Energy {'outperforming' if d >= 0 else 'underperforming'} Tech by {d:+.1f}pp.",
                     1 if d >= 0 else -1)

    if not g_votes:
        return None
    g_score = sum(g_votes)
    i_score = sum(i_votes) if i_votes else 0

    growth_up = g_score > 0
    infl_up = i_score > 0
    if growth_up and not infl_up:
        quad = 1
    elif growth_up and infl_up:
        quad = 2
    elif not growth_up and infl_up:
        quad = 3
    else:
        quad = 4

    pb = _PLAYBOOK[quad]
    conviction = "high" if abs(g_score) >= 3 else "moderate" if abs(g_score) >= 2 else "low"

    out = {
        "as_of": (sectors or factors)["as_of"],
        "quad": quad, "quad_name": pb["name"], "quad_tag": pb["tag"],
        "growth": "accelerating" if growth_up else "decelerating", "growth_score": g_score,
        "inflation": "accelerating" if infl_up else "decelerating", "inflation_score": i_score,
        "conviction": conviction,
        "playbook": {k: pb[k] for k in ("best_sectors", "best_factors", "best_assets", "momentum_note")},
        "evidence": evidence,
    }
    out["interpretation_points"] = _interpret(out)
    return out


def _interpret(o):
    pb = _PLAYBOOK[o["quad"]]
    pts = [
        {"label": f"Market-implied Quad {o['quad']}: {o['quad_name']}", "detail":
            f"Cross-asset behaviour is trading like {pb['tag']} ({o['conviction']} conviction). "
            "This is inferred from how the market is positioned — not a GDP/CPI nowcast."},
        {"label": "Growth", "detail":
            f"Growth signals net {o['growth']} (score {o['growth_score']:+}) — from sector leadership, the beta/momentum "
            "factors, breadth and credit."},
        {"label": "Inflation", "detail":
            f"Inflation signals net {o['inflation']} (score {o['inflation_score']:+}) — inferred from energy/materials "
            "leadership (the weaker-inferred axis on free data)."},
        {"label": "Playbook", "detail":
            f"Favor {', '.join(pb['best_sectors'][:4])}; factors {', '.join(pb['best_factors'][:3])}."},
        {"label": "For a momentum trader", "detail": pb["momentum_note"]},
    ]
    return pts
