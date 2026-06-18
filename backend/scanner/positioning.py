"""Market positioning — forward-looking regime indicators (the "who's exposed" layer).

Unlike price-derived indicators (which lag by construction), positioning data
shows who is exposed and how crowded the boat is. Extremes are contrarian:
maximum fear / washed-out positioning tends to precede rallies; maximum
complacency / crowded longs tend to precede air pockets.

Three free sources, combined into a contrarian "regime dial":

1. CFTC COT — leveraged-funds net position in E-mini S&P 500 + Nasdaq-100
   futures. Weekly (Fri 3:30pm ET, data as of Tue). Public Socrata API at
   publicreporting.cftc.gov (TFF futures-only dataset gpe5-46if).
   Leveraged funds ≈ hedge funds / CTAs — the closest free proxy to
   "CTA positioning". Z-scored against ~3 years of weekly history.

2. SPY put/call volume ratio — computed from Alpaca's options API by summing
   daily contract volume for near-dated puts vs calls. Daily.
   NOTE: this is a SPY-options proxy, not CBOE's equity-only ratio (CBOE
   blocks server scraping). SPY options skew put-heavy because the product is
   used for hedging — thresholds are calibrated for that (typical ~1.2–1.9).

3. NAAIM Exposure Index — average equity exposure of active managers.
   Weekly xlsx scraped from naaim.org. <30 = washed out, >90 = fully invested.

Each component votes contrarian at extremes:
  fear / washed-out  → +1 (opportunity)
  neutral            →  0
  complacent/crowded → −1 (reduce aggression)
The dial is the sum of available votes (−3 … +3).

All fetches degrade gracefully (component = None on failure) and results are
cached to disk for 12h — the underlying sources update weekly/daily.
"""
from __future__ import annotations

import json
import logging
import os
import re
import statistics
import time
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).parent.parent / "data" / "positioning.json"
CACHE_TTL_SECONDS = 12 * 3600

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ── Thresholds (documented on the /scoring page) ─────────────────────────────
COT_Z_EXTREME        = 1.5    # |z| beyond this = crowded positioning
PC_FEAR_THRESHOLD    = 2.0    # SPY P/C vol ratio above = fear extreme
PC_COMPLACENT_THRESHOLD = 1.1 # below = complacency (call-chasing)
NAAIM_WASHED_OUT     = 30.0   # below = managers washed out
NAAIM_FULLY_INVESTED = 90.0   # above = managers all-in


# ── 1) CFTC COT — leveraged funds net positioning ─────────────────────────────

_COT_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
_COT_CONTRACTS = {"es": "E-MINI S&P 500", "nq": "NASDAQ MINI"}


def _fetch_cot_contract(client: httpx.Client, name: str) -> dict | None:
    """~3 years of weekly leveraged-funds net positioning for one contract."""
    params = {
        "$where": f"contract_market_name='{name}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": "160",
        "$select": "report_date_as_yyyy_mm_dd,lev_money_positions_long,"
                   "lev_money_positions_short,open_interest_all",
    }
    r = client.get(_COT_URL, params=params, timeout=20)
    r.raise_for_status()
    rows = r.json()
    if len(rows) < 30:
        return None

    # net position as % of open interest, newest first
    net_pcts: list[float] = []
    for row in rows:
        oi = float(row.get("open_interest_all", 0) or 0)
        if oi <= 0:
            continue
        net = float(row.get("lev_money_positions_long", 0) or 0) - \
              float(row.get("lev_money_positions_short", 0) or 0)
        net_pcts.append(net / oi * 100)
    if len(net_pcts) < 30:
        return None

    latest = net_pcts[0]
    mean   = statistics.fmean(net_pcts)
    stdev  = statistics.stdev(net_pcts)
    z      = (latest - mean) / stdev if stdev > 0 else 0.0
    return {
        "net_pct_oi": round(latest, 1),
        "z": round(z, 2),
        "date": rows[0]["report_date_as_yyyy_mm_dd"][:10],
    }


def fetch_cot() -> dict | None:
    """Leveraged-funds positioning, ES + NQ blended. Contrarian at extremes."""
    with httpx.Client(headers=_UA) as client:
        es = _fetch_cot_contract(client, _COT_CONTRACTS["es"])
        nq = _fetch_cot_contract(client, _COT_CONTRACTS["nq"])
    if es is None and nq is None:
        return None
    zs = [c["z"] for c in (es, nq) if c]
    avg_z = sum(zs) / len(zs)

    if avg_z <= -COT_Z_EXTREME:
        state, vote = "crowded_short", +1     # shorts crowded → squeeze fuel
    elif avg_z >= COT_Z_EXTREME:
        state, vote = "crowded_long", -1      # longs crowded → no marginal buyer
    else:
        state, vote = "neutral", 0
    return {"es": es, "nq": nq, "avg_z": round(avg_z, 2), "state": state, "vote": vote}


# ── 2) SPY put/call volume ratio (Alpaca options API) ─────────────────────────

_ALPACA_OPTIONS_URL = "https://data.alpaca.markets/v1beta1/options/snapshots/SPY"


def _sum_option_volume(client: httpx.Client, opt_type: str, exp_lte: str) -> int | None:
    """Sum today's contract volume across the near-dated SPY chain (one side)."""
    total, pages, page_token = 0, 0, None
    while pages < 8:                                  # ≤8 pages × 1000 contracts
        params = {
            "feed": "indicative", "limit": "1000", "type": opt_type,
            "expiration_date_lte": exp_lte,
        }
        if page_token:
            params["page_token"] = page_token
        r = client.get(_ALPACA_OPTIONS_URL, params=params, timeout=25)
        r.raise_for_status()
        d = r.json()
        for snap in (d.get("snapshots") or {}).values():
            bar = snap.get("dailyBar") or {}
            total += int(bar.get("v", 0) or 0)
        pages += 1
        page_token = d.get("next_page_token")
        if not page_token:
            break
    return total


def fetch_put_call() -> dict | None:
    """SPY P/C volume ratio over expirations within ~35 days. Needs Alpaca keys."""
    key, sec = os.getenv("ALPACA_API_KEY", ""), os.getenv("ALPACA_API_SECRET", "")
    if not key or not sec:
        logger.info("put/call: Alpaca keys not set — skipping")
        return None
    exp_lte = (date.today() + timedelta(days=35)).isoformat()
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}
    with httpx.Client(headers=headers) as client:
        puts  = _sum_option_volume(client, "put", exp_lte)
        calls = _sum_option_volume(client, "call", exp_lte)
    if not puts or not calls:
        return None
    ratio = puts / calls

    if ratio >= PC_FEAR_THRESHOLD:
        state, vote = "fear", +1
    elif ratio <= PC_COMPLACENT_THRESHOLD:
        state, vote = "complacent", -1
    else:
        state, vote = "neutral", 0
    return {
        "ratio": round(ratio, 2), "put_vol": puts, "call_vol": calls,
        "state": state, "vote": vote,
    }


# ── 3) NAAIM Exposure Index ───────────────────────────────────────────────────

_NAAIM_PAGE = "https://naaim.org/programs/naaim-exposure-index/"


def fetch_naaim() -> dict | None:
    """Latest NAAIM number + z-score. Scrapes the weekly xlsx link off the page."""
    import pandas as pd

    with httpx.Client(headers=_UA, follow_redirects=True) as client:
        page = client.get(_NAAIM_PAGE, timeout=20)
        page.raise_for_status()
        m = re.search(r'https://naaim\.org/wp-content/uploads/[^"\']+\.xlsx', page.text)
        if not m:
            logger.warning("NAAIM: no xlsx link found on page")
            return None
        xls = client.get(m.group(0), timeout=30)
        xls.raise_for_status()

    df = pd.read_excel(BytesIO(xls.content))
    # Identify the date column and the mean-exposure column robustly:
    # the sheet has "Date" + "NAAIM Number" (a.k.a. mean/average) among quartiles.
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = next((cols[k] for k in cols if "date" in k), df.columns[0])
    val_col  = next((cols[k] for k in cols if "naaim" in k or "mean" in k or "average" in k), None)
    if val_col is None:                       # fall back: first numeric column
        num = df.select_dtypes("number")
        if num.empty:
            return None
        val_col = num.columns[0]

    # Sort by date ascending — the published sheet is newest-first
    df = df.assign(_dt=pd.to_datetime(df[date_col], errors="coerce")) \
           .dropna(subset=["_dt"]).sort_values("_dt")
    series = pd.to_numeric(df[val_col], errors="coerce").dropna()
    if len(series) < 30:
        return None
    latest = float(series.iloc[-1])
    z      = (latest - float(series.mean())) / float(series.std()) if series.std() > 0 else 0.0
    latest_date = str(df["_dt"].iloc[-1].date())

    if latest <= NAAIM_WASHED_OUT:
        state, vote = "washed_out", +1
    elif latest >= NAAIM_FULLY_INVESTED:
        state, vote = "fully_invested", -1
    else:
        state, vote = "neutral", 0
    return {"value": round(latest, 1), "z": round(z, 2), "date": latest_date,
            "state": state, "vote": vote}


# ── Composite dial ────────────────────────────────────────────────────────────

_DIAL_LABELS = {
    +3: ("Fear extreme — contrarian opportunity", "All three sources at fear/washed-out extremes. Historically the best forward returns."),
    +2: ("Strong contrarian support", "Multiple positioning extremes on the fear side — breakouts have fuel."),
    +1: ("Cautiously supportive", "One source at a fear extreme; positioning has room."),
     0: ("Neutral", "No positioning extremes — trade the setups, normal sizing."),
    -1: ("Getting crowded", "One source at a complacent/crowded extreme — tighten stops."),
    -2: ("Crowded — reduce aggression", "Multiple crowding extremes — late-cycle conditions, smaller size."),
    -3: ("Maximum complacency", "All sources crowded/complacent. Air-pocket risk — defensive."),
}


# ── 4) High-yield credit spread (FRED, no key) ────────────────────────────────
# ICE BofA US High Yield OAS. Credit LEADS equities: widening spreads precede
# risk-off. This is a DIRECTIONAL vote (not contrarian) — tight/easing = risk-on
# (+1), widening/stressed = risk-off (−1).
_FRED_HY_OAS = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"


def fetch_credit_spread() -> dict | None:
    try:
        with httpx.Client() as client:
            r = client.get(_FRED_HY_OAS, timeout=20)
        r.raise_for_status()
        rows: list[tuple[str, float]] = []
        for line in r.text.strip().splitlines()[1:]:
            parts = line.split(",")
            if len(parts) < 2:
                continue
            d, v = parts[0], parts[-1].strip()
            if v in (".", ""):
                continue
            try:
                rows.append((d, float(v)))
            except ValueError:
                continue
        if len(rows) < 30:
            return None
    except Exception as e:
        logger.info("credit spread fetch failed: %s", e)
        return None

    cur = rows[-1][1]
    mo_ago = rows[max(0, len(rows) - 22)][1]
    change_1m = round(cur - mo_ago, 2)
    window = [v for _, v in rows[-756:]]
    mean = sum(window) / len(window)
    std = (sum((x - mean) ** 2 for x in window) / len(window)) ** 0.5 or 1.0
    z = round((cur - mean) / std, 2)

    if change_1m >= 0.4 or z >= 1.5:          # widening fast or stressed → risk-off
        state, vote = "widening", -1
    elif change_1m <= -0.25 and z <= 0.0:     # tightening and below average → risk-on
        state, vote = "tightening", 1
    else:
        state, vote = "neutral", 0
    return {"oas": round(cur, 2), "change_1m": change_1m, "z": z,
            "date": rows[-1][0], "state": state, "vote": vote}


def compute_cta_levels(symbol: str = "SPY") -> dict | None:
    """Rough 'where do trend-followers (CTAs) flip' gauge.

    CTAs are systematic trend-followers whose long/short triggers are moving-average
    based. We can't see their proprietary models, but the index's distance to its
    50/100/200-day SMAs is a free proxy: above all three = CTAs positioned long; the
    nearest MA below price is the rough first de-gross trigger; below all three = short.
    """
    from .fetcher import fetch_ohlcv
    df = fetch_ohlcv(symbol, period_days=340)
    if df is None or len(df) < 200:
        return None
    c = df["close"]
    price = float(c.iloc[-1])
    levels = []
    for ma in (50, 100, 200):
        v = float(c.rolling(ma).mean().iloc[-1])
        levels.append({"ma": ma, "value": round(v, 2),
                       "dist_pct": round((price / v - 1) * 100, 1), "above": price > v})
    above = sum(1 for l in levels if l["above"])
    state = {3: "trend_long", 2: "long", 1: "de_grossing", 0: "short"}[above]
    below_lv = [l for l in levels if l["above"]]
    above_lv = [l for l in levels if not l["above"]]
    if below_lv:                              # nearest MA below price = first de-gross trigger
        flip = min(below_lv, key=lambda l: price - l["value"])
    else:                                     # below all → nearest MA above = re-gross trigger
        flip = min(above_lv, key=lambda l: l["value"] - price)

    if state == "trend_long":
        interp = (f"{symbol} is above its 50/100/200-day — trend-followers are positioned long. First de-gross "
                  f"trigger ≈ ${flip['value']} (the {flip['ma']}-day, {abs(round((price/flip['value']-1)*100,1))}% below); "
                  "a break there starts mechanical selling.")
    elif state == "short":
        interp = (f"{symbol} is below all three MAs — CTAs are positioned short. A reclaim of ≈ ${flip['value']} "
                  f"(the {flip['ma']}-day) starts mechanical buying / short-covering.")
    else:
        interp = (f"{symbol} is above {above} of the three MAs — CTAs are partially de-grossed. The {flip['ma']}-day "
                  f"≈ ${flip['value']} is the swing trigger.")

    return {"symbol": symbol, "price": round(price, 2), "levels": levels,
            "above_count": above, "state": state,
            "flip_ma": flip["ma"], "flip_value": flip["value"], "interpretation": interp}


def _build() -> dict:
    cot = pc = naaim = credit = None
    cta = None
    try:
        cot = fetch_cot()
    except Exception as e:
        logger.warning("COT fetch failed: %s", e)
    try:
        pc = fetch_put_call()
    except Exception as e:
        logger.warning("put/call fetch failed: %s", e)
    try:
        naaim = fetch_naaim()
    except Exception as e:
        logger.warning("NAAIM fetch failed: %s", e)
    try:
        credit = fetch_credit_spread()
    except Exception as e:
        logger.warning("credit spread fetch failed: %s", e)
    try:
        cta = compute_cta_levels()
    except Exception as e:
        logger.warning("CTA levels failed: %s", e)

    votes = [c["vote"] for c in (cot, pc, naaim, credit) if c]
    score = sum(votes)
    label, detail = _DIAL_LABELS.get(max(-3, min(3, score)), _DIAL_LABELS[0])
    return {
        "as_of": date.today().isoformat(),
        "cot": cot,
        "put_call": pc,
        "naaim": naaim,
        "credit": credit,
        "cta": cta,
        "sources_available": len(votes),
        "dial": {"score": score, "label": label, "detail": detail},
    }


def get_positioning(force: bool = False) -> dict:
    """Cached composite (12h TTL) — sources update weekly/daily."""
    if not force and CACHE_PATH.exists():
        try:
            age = time.time() - CACHE_PATH.stat().st_mtime
            if age < CACHE_TTL_SECONDS:
                return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    result = _build()
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(result))
    except Exception as e:
        logger.warning("positioning cache write failed: %s", e)
    return result
