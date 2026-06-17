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


# Per-horizon config: which lookback key each input uses.
#   monthly  = intermediate-term "weather"  (~1-month signals, 50-DMA breadth, 1mo credit change)
#   quarterly= longer-term "climate"         (~3-month signals, 200-DMA breadth, credit z-level)
_HORIZONS = {
    "monthly":   {"sector_key": "m1", "factor_key": "m1", "breadth_field": "pct_above_50dma",
                  "breadth_lbl": "50-DMA", "credit_field": "change_1m"},
    "quarterly": {"sector_key": "m3", "factor_key": "m3", "breadth_field": "pct_above_200dma",
                  "breadth_lbl": "200-DMA", "credit_field": "z"},
}
_HZ_LBL = {"monthly": "1-month", "quarterly": "3-month"}


def _score_horizon(hz: str, sectors, factors, breadth, credit) -> dict | None:
    cfg = _HORIZONS[hz]
    sk, fk = cfg["sector_key"], cfg["factor_key"]
    hzlbl = _HZ_LBL[hz]
    g_votes, i_votes, evidence = [], [], []

    def vote(axis, label, detail, v):
        (g_votes if axis == "growth" else i_votes).append(v)
        evidence.append({"axis": axis, "label": label, "detail": detail, "vote": v})

    rel = {}
    if sectors:
        rel = {r["symbol"]: (r.get("rel") or {}) for r in sectors["sectors"]}
        cyc = [rel[s][sk] for s in _CYCLICAL if rel.get(s, {}).get(sk) is not None]
        dfv = [rel[s][sk] for s in _DEFENSIVE if rel.get(s, {}).get(sk) is not None]
        if cyc and dfv:
            tilt = sum(cyc) / len(cyc) - sum(dfv) / len(dfv)
            vote("growth", "Sector leadership",
                 f"Cyclicals {'leading' if tilt >= 0 else 'lagging'} defensives by {tilt:+.1f}pp ({hzlbl} RS).",
                 1 if tilt >= 0 else -1)
    if factors:
        fmap = {f["factor"]: f for f in factors["factors"]}
        for fname, lbl, up, dn in [("Beta", "Risk appetite (Beta)", "high-beta leading", "low-beta leading"),
                                   ("Momentum", "Momentum factor", "in gear", "out of favor")]:
            sp = fmap.get(fname, {}).get("spread", {}).get(fk)
            if sp is not None:
                vote("growth", lbl, f"{(up if sp >= 0 else dn).capitalize()} ({sp:+}% {hzlbl}).", 1 if sp >= 0 else -1)
    if breadth and breadth.get(cfg["breadth_field"]) is not None:
        pv = breadth[cfg["breadth_field"]]
        vote("growth", "Market breadth",
             f"{pv}% of large caps above their {cfg['breadth_lbl']} — participation {'healthy' if pv >= 50 else 'thin'}.",
             1 if pv >= 50 else -1)
    if credit and credit.get(cfg["credit_field"]) is not None:
        cv = credit[cfg["credit_field"]]
        if hz == "monthly":
            vote("growth", "Credit (HY OAS, 1mo)",
                 f"HY spreads {'tightening' if cv <= 0 else 'widening'} {cv:+}pp over the month.", 1 if cv <= 0 else -1)
        else:
            vote("growth", "Credit (HY OAS, z-score)",
                 f"HY spreads {'below' if cv <= 0 else 'above'} their multi-year average (z {cv:+}).", 1 if cv <= 0 else -1)

    # Inflation axis
    if rel:
        infl = [rel[s][sk] for s in _INFLATION if rel.get(s, {}).get(sk) is not None]
        if infl:
            avg = sum(infl) / len(infl)
            vote("inflation", "Energy/Materials leadership",
                 f"Energy + Materials {'leading' if avg >= 0 else 'lagging'} the market ({avg:+.1f}pp {hzlbl}).",
                 1 if avg >= 0 else -1)
        xle, xlk = rel.get("XLE", {}).get(sk), rel.get("XLK", {}).get(sk)
        if xle is not None and xlk is not None:
            d = xle - xlk
            vote("inflation", "Real assets vs growth",
                 f"Energy {'outperforming' if d >= 0 else 'underperforming'} Tech by {d:+.1f}pp ({hzlbl}).",
                 1 if d >= 0 else -1)

    if not g_votes:
        return None
    g, i = sum(g_votes), (sum(i_votes) if i_votes else 0)
    quad = 1 if (g > 0 and i <= 0) else 2 if (g > 0 and i > 0) else 3 if (g <= 0 and i > 0) else 4
    pb = _PLAYBOOK[quad]
    return {
        "quad": quad, "quad_name": pb["name"], "quad_tag": pb["tag"],
        "growth": "accelerating" if g > 0 else "decelerating", "growth_score": g,
        "inflation": "accelerating" if i > 0 else "decelerating", "inflation_score": i,
        "conviction": "high" if abs(g) >= 3 else "moderate" if abs(g) >= 2 else "low",
        "playbook": {k: pb[k] for k in ("best_sectors", "best_factors", "best_assets", "momentum_note")},
        "evidence": evidence,
    }


def _compute() -> dict | None:
    from .sectors import get_sector_rotation
    from .factors import get_factor_leadership
    from .breadth import get_breadth
    from .positioning import fetch_credit_spread

    sectors = get_sector_rotation()
    factors = get_factor_leadership()
    if sectors is None and factors is None:
        return None
    breadth = get_breadth()
    try:
        credit = fetch_credit_spread()
    except Exception:
        credit = None

    monthly = _score_horizon("monthly", sectors, factors, breadth, credit)
    quarterly = _score_horizon("quarterly", sectors, factors, breadth, credit)
    if monthly is None and quarterly is None:
        return None

    aligned = bool(monthly and quarterly and monthly["quad"] == quarterly["quad"])
    out = {
        "as_of": (sectors or factors)["as_of"],
        "monthly": monthly,        # weather — intermediate-term tactical
        "quarterly": quarterly,    # climate — longer-term dominant regime
        "aligned": aligned,
    }
    out["interpretation_points"] = _interpret(out)
    return out


def _interpret(o):
    m, q = o.get("monthly"), o.get("quarterly")
    pts = []
    if q:
        pts.append({"label": f"Climate — Quarterly Quad {q['quad']}: {q['quad_name']}", "detail":
            f"The dominant ~3-month regime is trading like {q['quad_tag']} ({q['conviction']} conviction). "
            "This is the bigger backdrop — it sets your default posture."})
    if m:
        pts.append({"label": f"Weather — Monthly Quad {m['quad']}: {m['quad_name']}", "detail":
            f"The intermediate ~1-month overlay is {m['quad_tag']} ({m['conviction']} conviction). "
            "This is the tactical, faster-moving read for timing exposure."})
    if m and q:
        if o["aligned"]:
            pts.append({"label": "Aligned", "detail":
                f"Weather and climate agree on Quad {m['quad']} — a high-confidence regime; lean into its playbook."})
        else:
            pts.append({"label": "Diverging — regime in transition", "detail":
                f"The monthly (weather) has shifted to Quad {m['quad']} while the quarterly (climate) is still Quad "
                f"{q['quad']}. Watch for a regime change; respect the climate but size to the weather."})
    # Tactical playbook from the monthly read (fall back to quarterly)
    drive = m or q
    if drive:
        pb = drive["playbook"]
        pts.append({"label": "Playbook (tactical)", "detail":
            f"Favor {', '.join(pb['best_sectors'][:4])}; factors {', '.join(pb['best_factors'][:3])}."})
        pts.append({"label": "For a momentum trader", "detail": pb["momentum_note"]})
    pts.append({"label": "Honest caveat", "detail":
        "Market-implied — inferred from how the tape is positioned, not a GDP/CPI nowcast. The inflation axis is the "
        "weaker-inferred one on free data."})
    return pts
