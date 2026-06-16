"""Per-symbol options analytics — a forward-looking ("leading") layer.

Options prices encode the market's EXPECTATIONS (future volatility + direction),
so unlike price/volume/MA signals — which only describe what already happened —
they are genuinely forward-looking. This module distils a near-dated chain into a
handful of leading tells:

  - implied volatility (ATM IV)               — how big a move is priced in
  - options-implied EXPECTED MOVE (straddle)  — the ± range by expiry (great for
                                                sizing EP/catalyst targets & stops)
  - put/call SKEW (OTM put IV − OTM call IV)  — downside fear vs upside demand
  - put/call ratios (volume + open interest)  — sentiment (contrarian at extremes)
  - unusual activity (volume ÷ open interest) — fresh positioning, and which side

Data source (dual, automatic fallback):
  - PRIMARY: yfinance option chains (free, includes IV / OI / volume) → the full
    card incl. OI-based metrics (P/C OI, max pain, ACI, OI walls). Used locally.
  - FALLBACK: Alpaca options snapshots (`/v1beta1/options/snapshots`) — used when
    yfinance is blocked (cloud IPs like Render). Alpaca's FREE "indicative" feed
    returns quotes + volume but NO open interest / IV / greeks, so we invert IV
    from bid/ask mids via Black-Scholes and the OI-based metrics come back null.
The output shape is identical for both; the `source` field says which was used.

Like the Fibonacci grid, this is a CONFLUENCE / CONTEXT layer — NOT a P Score input.
"""
from __future__ import annotations

import logging
import math
import os
import re
import time
from datetime import date

logger = logging.getLogger(__name__)

# Skew sampling: compare IV of options ~this far OTM on each side.
_OTM_PCT = 0.10
# How many near-dated expiries to aggregate for the put/call ratios.
_MAX_EXPIRIES = 3
# Simple in-process cache (symbol → (timestamp, result)); options change slowly.
_CACHE: dict[str, tuple[float, dict | None]] = {}
_TTL_SEC = 900  # 15 min

# Delta-adjusted OI (ACI level) — Black-Scholes delta inputs.
_RISK_FREE = 0.04      # annualised risk-free rate
_ACI_THRESH = 0.15     # |sentiment| above this = directional, else neutral


def _mid(row) -> float:
    """Mid price from bid/ask, falling back to last traded price."""
    bid = float(row.get("bid", 0) or 0)
    ask = float(row.get("ask", 0) or 0)
    if bid > 0 and ask > 0:
        return (bid + ask) / 2
    last = float(row.get("lastPrice", 0) or 0)
    return last


def _nearest_row(df, strike_target: float):
    """Row whose strike is closest to ``strike_target`` (or None if empty)."""
    if df is None or len(df) == 0:
        return None
    idx = (df["strike"] - strike_target).abs().idxmin()
    return df.loc[idx]


def _max_pain(call_oi: dict[float, float], put_oi: dict[float, float]) -> float | None:
    """Max-pain strike: the settlement price that minimises the total in-the-money
    payoff owed to option holders at expiry — the level price tends to gravitate
    toward into expiration (option writers' break-even / 'pin')."""
    strikes = sorted(set(call_oi) | set(put_oi))
    if len(strikes) < 3:
        return None
    best_k, best_pain = None, float("inf")
    for s in strikes:
        pain = 0.0
        for k, oi in call_oi.items():
            if s > k:
                pain += oi * (s - k)      # ITM calls pay out
        for k, oi in put_oi.items():
            if s < k:
                pain += oi * (k - s)      # ITM puts pay out
        if pain < best_pain:
            best_pain, best_k = pain, s
    return best_k


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_delta(opt_type: str, S: float, K: float, T: float, sigma: float,
              r: float = _RISK_FREE) -> float | None:
    """Black-Scholes delta. Calls ∈ (0,1); puts ∈ (-1,0). None if inputs invalid."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return None
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1) if opt_type == "call" else _norm_cdf(d1) - 1.0


def _bs_price(opt_type: str, S: float, K: float, T: float, sigma: float,
              r: float = _RISK_FREE) -> float:
    """Black-Scholes option price — used to invert IV from a market mid."""
    if sigma <= 0 or T <= 0:
        return max(0.0, (S - K) if opt_type == "call" else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "call":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def _implied_vol(opt_type: str, price: float, S: float, K: float, T: float,
                 r: float = _RISK_FREE) -> float | None:
    """Invert IV from an option mid via bisection. Returns σ as a fraction, or None
    if the price is outside the invertible range (stale / crossed quote)."""
    if price <= 0 or S <= 0 or K <= 0 or T <= 0:
        return None
    lo, hi = 1e-4, 5.0
    if not (_bs_price(opt_type, S, K, T, lo, r) <= price <= _bs_price(opt_type, S, K, T, hi, r)):
        return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        pm = _bs_price(opt_type, S, K, T, mid, r)
        if abs(pm - price) < 1e-4:
            return mid
        if pm < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _parse_occ(sym: str):
    """OCC option symbol (e.g. NVTS260618C00012000) → (expiry_date, 'call'|'put', strike)."""
    m = re.match(r"^[A-Z]+(\d{6})([CP])(\d{8})$", sym)
    if not m:
        return None
    ymd, cp, strike = m.groups()
    try:
        exp = date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
    except ValueError:
        return None
    return exp, ("call" if cp == "C" else "put"), int(strike) / 1000.0


def _bs_gamma(S: float, K: float, T: float, sigma: float, r: float = _RISK_FREE) -> float:
    """Black-Scholes gamma (same for calls and puts)."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    pdf = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    return pdf / (S * sigma * math.sqrt(T))


def _gex(contracts: list[dict], spot: float, max_dte: int = 45) -> dict | None:
    """Dealer Gamma Exposure. contracts: [{type, strike, oi, iv, dte}].

    Convention: dealers are long call gamma and short put gamma (the standard
    retail GEX assumption). Positive net GEX → dealers dampen moves (price pins,
    vol suppressed); negative → they amplify moves (trend/volatility). The
    zero-gamma 'flip' is the price where net dealer gamma crosses zero — a leading
    regime line (above = pinned, below = accelerant)."""
    rows = [c for c in contracts if 0 <= c["dte"] <= max_dte and c["oi"] > 0 and c["iv"] > 0]
    if not rows:
        return None

    def net_at(S: float) -> float:
        tot = 0.0
        for c in rows:
            g = _bs_gamma(S, c["strike"], max(c["dte"], 1) / 365.0, c["iv"])
            tot += (g if c["type"] == "call" else -g) * c["oi"]
        return tot

    raw = net_at(spot)
    gex_musd = round(raw * 100 * spot * spot * 0.01 / 1e6, 1)   # $ per 1% move, in $M
    regime = "positive" if gex_musd > 0 else "negative"

    # Zero-gamma flip: scan ±40% around spot for the sign change.
    flip, lo, hi, steps = None, spot * 0.6, spot * 1.4, 60
    prev_s = prev_n = None
    for i in range(steps + 1):
        S = lo + (hi - lo) * i / steps
        n = net_at(S)
        if prev_n is not None and ((prev_n < 0 <= n) or (prev_n > 0 >= n)) and n != prev_n:
            flip = round(prev_s + (S - prev_s) * (0 - prev_n) / (n - prev_n), 2)
            break
        prev_s, prev_n = S, n

    # Gamma walls: strikes with the most gamma×OI (call above spot, put below).
    cg: dict[float, float] = {}
    pg: dict[float, float] = {}
    for c in rows:
        g = _bs_gamma(spot, c["strike"], max(c["dte"], 1) / 365.0, c["iv"]) * c["oi"]
        (cg if c["type"] == "call" else pg)[c["strike"]] = \
            (cg if c["type"] == "call" else pg).get(c["strike"], 0.0) + g
    call_wall = max((k for k in cg if k > spot), key=lambda k: cg[k], default=None)
    put_wall = max((k for k in pg if k < spot), key=lambda k: pg[k], default=None)

    return {"gex_musd": gex_musd, "regime": regime, "flip": flip,
            "call_wall": round(call_wall, 2) if call_wall else None,
            "put_wall": round(put_wall, 2) if put_wall else None}


def _term_structure(contracts: list[dict], spot: float) -> dict | None:
    """IV term structure: front-expiry ATM IV vs a ~45-day back-expiry ATM IV.
    Backwardation (front > back) = near-term event/stress priced in (leading)."""
    by_dte: dict[int, list] = {}
    for c in contracts:
        if c["iv"] > 0:
            by_dte.setdefault(c["dte"], []).append(c)
    dtes = sorted(by_dte)
    if len(dtes) < 2:
        return None

    def atm_iv(rows):
        return min(rows, key=lambda r: abs(r["strike"] - spot))["iv"]

    front_dte = dtes[0]
    back_dte = min((d for d in dtes if d > front_dte), key=lambda d: abs(d - 45), default=None)
    if back_dte is None:
        return None
    fiv, biv = atm_iv(by_dte[front_dte]), atm_iv(by_dte[back_dte])
    if fiv <= 0 or biv <= 0:
        return None
    ratio = round(fiv / biv, 2)
    state = "backwardation" if ratio >= 1.05 else "contango" if ratio <= 0.95 else "flat"
    return {"front_dte": front_dte, "front_iv": round(fiv * 100, 1),
            "back_dte": back_dte, "back_iv": round(biv * 100, 1),
            "ratio": ratio, "state": state}


def _interpret_points(o: dict, spot: float) -> list[dict]:
    """Per-metric plain-English interpretation as labelled bullets — each reads the
    metric's value AND explains what it means for this stock. Skips metrics the data
    source omits (e.g. OI on the Alpaca fallback)."""
    pts: list[dict] = []
    lean, dte, exp = o.get("lean", "neutral"), o.get("dte"), o.get("nearest_expiry")

    pts.append({"label": "Outlook", "detail":
        f"Options are leaning {lean} over the next ~{dte} days. This is leading context — how traders are "
        "positioned and what they're paying for — not a standalone buy/sell trigger."})

    iv, hv, ivr, ivs = o.get("atm_iv"), o.get("hv"), o.get("iv_hv"), o.get("iv_state")
    if iv is not None:
        d = f"Implied volatility is {iv}% — the size of move the market expects (annualised)."
        if ivs == "cheap" and hv:
            d += (f" That's below the {hv}% the stock has actually realised (IV Rank {ivr}×), so options look cheap — "
                  "the market may be underpricing the next move; cheap premium favours buying options / breakouts over selling.")
        elif ivs == "rich" and hv:
            d += (f" That's above the {hv}% realised (IV Rank {ivr}×), so options are expensive — a fear or pre-catalyst "
                  "premium is priced in, and an IV crush is a risk if the event passes quietly.")
        elif hv:
            d += f" Roughly in line with the {hv}% realised (IV Rank {ivr}×) — fairly priced."
        pts.append({"label": "Implied volatility & IV Rank", "detail": d})

    emp, ema = o.get("expected_move_pct"), o.get("expected_move_abs")
    if emp is not None and spot > 0:
        lo, hi = round(spot * (1 - emp / 100), 2), round(spot * (1 + emp / 100), 2)
        pts.append({"label": "Expected move", "detail":
            f"The market is pricing a ±{emp}% move (±${ema}) by {exp} — the at-the-money straddle, i.e. the range traders "
            f"are actually paying for. That puts the realistic swing band around ${lo}–${hi}; keep targets and stops inside "
            "it, because a target beyond that band is a statistical stretch for this expiry."})

    sk = o.get("skew")
    if sk is not None:
        d = "Skew compares out-of-the-money put IV with call IV — fear (puts bid up) vs upside demand (calls bid up)."
        d += (f" Here it's negative ({sk}): traders are paying up for upside calls — a bullish tell." if sk < -1
              else f" Here it's elevated (+{sk}): demand for downside protection — a cautious/bearish tell." if sk > 3
              else f" Here it's roughly flat ({sk}): no strong directional bias at the wings.")
        pts.append({"label": "Skew", "detail": d})

    pcv = o.get("put_call_vol")
    if pcv is not None:
        d = f"Put÷call volume today is {pcv}."
        d += (" Call-heavy flow (more calls than puts) — a bullish lean; it's a sentiment gauge, contrarian at extremes." if pcv < 0.7
              else " Put-heavy flow — a defensive/bearish lean (contrarian at extremes)." if pcv > 1.2
              else " Roughly balanced flow.")
        pts.append({"label": "Put/call volume", "detail": d})

    pco = o.get("put_call_oi")
    if pco is not None:
        pts.append({"label": "Put/call open interest", "detail":
            f"Resting open interest is {pco} puts per call — positions already on the book, slower-moving and less noisy than daily volume."})

    aci = o.get("aci_score")
    if aci is not None:
        bd, sd = o.get("bull_daoi", 0), o.get("bear_daoi", 0)
        pts.append({"label": "Accumulation (delta-adjusted OI)", "detail":
            f"Net positioning is {o.get('aci_label')} ({aci:+}) — call open interest minus put, weighted by each option's "
            f"delta so far-OTM lottery strikes count less ({bd:,} bullish vs {sd:,} bearish). +1 = fully net-long, "
            "−1 = net-short; often the cleanest single positioning tell."})

    mp = o.get("max_pain")
    if mp is not None:
        dd = o.get("max_pain_dist_pct") or 0
        d = (f"Max pain — the strike where option holders lose most and writers pay least, a mild 'pin' into expiry — "
             f"sits at ${mp} ({abs(dd)}% {'above' if dd > 0 else 'below'} price).")
        if abs(dd) <= 3 or (dte or 0) > 14:
            d += " It's near the money and weeks out, so it exerts little directional pull now (the pin only bites in the last days before expiry)."
        pts.append({"label": "Max pain", "detail": d})

    res, sup = o.get("oi_resistance") or [], o.get("oi_support") or []
    if res or sup:
        bits = []
        if res:
            bits.append("heavy call OI overhead at " + ", ".join(f"${l['strike']}" for l in res) + " is potential resistance where rallies may stall")
        if sup:
            bits.append("heavy put OI below at " + ", ".join(f"${l['strike']}" for l in sup) + " is potential support where dips may be defended")
        pts.append({"label": "Open-interest walls", "detail":
            "The biggest open-interest clusters act like barriers: " + "; ".join(bits) + "."})
    elif aci is None:
        pts.append({"label": "Open-interest metrics", "detail":
            "P/C OI, max pain, ACI and OI walls aren't available from the current fallback data source (they need open interest)."})

    gex = o.get("gex")
    if gex:
        if gex["regime"] == "positive":
            d = ("Dealer gamma is positive — dealers are long gamma, so they sell rallies and buy dips, which dampens "
                 "moves and tends to pin the price (mean-reverting, vol suppressed).")
        else:
            d = ("Dealer gamma is negative — dealers are short gamma, so they buy rallies and sell dips, which amplifies "
                 "moves (trend / volatility expansion — breakouts tend to run further).")
        if gex.get("flip"):
            d += f" The zero-gamma flip is ${gex['flip']}: above it dealers stabilise, below it they accelerate — watch that line."
        walls = []
        if gex.get("call_wall"):
            walls.append(f"call-gamma wall ${gex['call_wall']} (overhead pin/resistance)")
        if gex.get("put_wall"):
            walls.append(f"put-gamma wall ${gex['put_wall']} (downside pin/support)")
        if walls:
            d += " Gamma magnets: " + "; ".join(walls) + "."
        pts.append({"label": "Dealer gamma (GEX)", "detail": d})

    term = o.get("term_structure")
    if term:
        d = (f"IV term structure: front {term['front_dte']}d at {term['front_iv']}% vs {term['back_dte']}d at "
             f"{term['back_iv']}% — {term['state']}.")
        if term["state"] == "backwardation":
            d += " Near-term IV is bid above longer-dated, so the market is pricing an imminent event/catalyst — expect a move soon."
        elif term["state"] == "contango":
            d += " Normal upward slope — no near-term event premium; calmer regime."
        else:
            d += " Roughly flat — no strong near-term event signal."
        pts.append({"label": "IV term structure", "detail": d})

    pts.append({"label": "Bottom line", "detail":
        f"Net, options lean {lean} — but this is confluence, not a signal. Confirm direction with price and the firing "
        "setup before acting, and remember the read fades within ~a month."})
    return pts


def compute_options(symbol: str, spot: float, max_days: int = 60,
                    hv30: float | None = None, min_dte: int = 7,
                    target_dte: int = 30) -> dict | None:
    """Compute the leading-options snapshot for ``symbol`` at the given ``spot``.

    ``hv30`` is the 30-day annualised realised (historical) volatility as a
    fraction (e.g. 0.85 = 85%). When supplied, the snapshot adds IBKR's IV Rank
    (30-day IV ÷ 30-day HV) — the volatility risk premium that tells you whether
    options are rich or cheap relative to how the stock is actually moving.

    Expiry selection is swing-tuned: contracts expiring within ``min_dte`` days
    (default 7 — the noisy, theta-dominated current-week weeklies) are skipped,
    and the read is anchored to the expiry closest to ``target_dte`` (default 30,
    the standard monthly / IV horizon) so the expected move & IV are useful for a
    multi-day swing rather than a 3-day scalp.

    Returns a JSON-serialisable dict, or None if no usable chain is available.
    """
    now = time.time()
    cached = _CACHE.get(symbol)
    if cached and now - cached[0] < _TTL_SEC:
        return cached[1]

    result = _compute(symbol, spot, max_days, hv30, min_dte, target_dte)
    if result is not None:
        pts = _interpret_points(result, spot)
        result["interpretation_points"] = pts                       # [{label, detail}] for the UI
        result["interpretation"] = " ".join(p["detail"] for p in pts)  # flat paragraph (agent / fallback)
    _CACHE[symbol] = (now, result)
    return result


def _compute(symbol: str, spot: float, max_days: int, hv30: float | None = None,
             min_dte: int = 7, target_dte: int = 30) -> dict | None:
    """Source dispatch (first that succeeds wins):
      1. CBOE delayed-quotes CDN — full chain incl. OI / IV / greeks, free, no key,
         and datacenter-friendly (works on cloud IPs like Render).
      2. yfinance — full chain, but blocked on cloud IPs.
      3. Alpaca quotes — no OI; IV inverted via Black-Scholes (OI metrics null).
    """
    for fn in (_compute_cboe, _compute_yf, _compute_alpaca):
        res = fn(symbol, spot, max_days, hv30, min_dte, target_dte)
        if res is not None:
            return res
    return None


def _compute_yf(symbol: str, spot: float, max_days: int, hv30: float | None = None,
                min_dte: int = 7, target_dte: int = 30) -> dict | None:
    try:
        import yfinance as yf
    except Exception:
        return None
    if spot <= 0:
        return None

    try:
        tk = yf.Ticker(symbol)
        exps = list(tk.options or [])
    except Exception as e:
        logger.debug("options: no expirations for %s: %s", symbol, e)
        return None
    if not exps:
        return None

    today = date.today()
    def _dte(e: str) -> int:
        try:
            return (date.fromisoformat(e) - today).days
        except Exception:
            return 9999

    # Swing-tuned expiry selection: skip the noisy current-week weeklies (< min_dte)
    # and anchor to the expiry closest to target_dte (~30d, the monthly/IV horizon).
    usable = sorted([e for e in exps if min_dte <= _dte(e) <= max_days], key=_dte)
    if not usable:
        usable = sorted(exps, key=_dte)[:1]          # fallback: soonest available
    nearest = min(usable, key=lambda e: abs(_dte(e) - target_dte))   # the anchor expiry
    near = sorted(sorted(usable, key=lambda e: abs(_dte(e) - _dte(nearest)))[:_MAX_EXPIRIES], key=_dte)
    dte = max(_dte(nearest), 0)

    # ── Aggregate volume / open interest across the near expiries ──────────────
    call_vol = put_vol = call_oi = put_oi = 0.0
    bull_daoi = bear_daoi = 0.0                 # delta-adjusted OI (ACI level)
    nearest_calls = nearest_puts = None
    call_oi_strikes: dict[float, float] = {}   # strike → OI (for max pain + OI walls)
    put_oi_strikes: dict[float, float] = {}
    for e in near:
        try:
            oc = tk.option_chain(e)
        except Exception:
            continue
        c, p = oc.calls, oc.puts
        call_vol += float(c["volume"].fillna(0).sum())
        put_vol  += float(p["volume"].fillna(0).sum())
        call_oi  += float(c["openInterest"].fillna(0).sum())
        put_oi   += float(p["openInterest"].fillna(0).sum())
        T_e = max(_dte(e), 1) / 365.0
        for k, oi, iv in zip(c["strike"], c["openInterest"].fillna(0), c["impliedVolatility"].fillna(0)):
            call_oi_strikes[float(k)] = call_oi_strikes.get(float(k), 0.0) + float(oi)
            d = _bs_delta("call", spot, float(k), T_e, float(iv))
            if d:
                bull_daoi += float(oi) * d        # call delta-adjusted OI = bullish exposure
        for k, oi, iv in zip(p["strike"], p["openInterest"].fillna(0), p["impliedVolatility"].fillna(0)):
            put_oi_strikes[float(k)] = put_oi_strikes.get(float(k), 0.0) + float(oi)
            d = _bs_delta("put", spot, float(k), T_e, float(iv))
            if d:
                bear_daoi += float(oi) * abs(d)   # put delta-adjusted OI = bearish exposure
        if e == nearest:
            nearest_calls, nearest_puts = c, p

    if nearest_calls is None or len(nearest_calls) == 0 or nearest_puts is None:
        return None

    pc_vol = round(put_vol / call_vol, 2) if call_vol > 0 else None
    pc_oi  = round(put_oi / call_oi, 2) if call_oi > 0 else None

    # ── ATM implied volatility (avg of nearest-strike call & put) ──────────────
    atm_c = _nearest_row(nearest_calls, spot)
    atm_p = _nearest_row(nearest_puts, spot)
    iv_c = float(atm_c["impliedVolatility"]) if atm_c is not None else float("nan")
    iv_p = float(atm_p["impliedVolatility"]) if atm_p is not None else float("nan")
    ivs = [v for v in (iv_c, iv_p) if v and not math.isnan(v) and v > 0]
    atm_iv = round(sum(ivs) / len(ivs) * 100, 1) if ivs else None   # in %

    # ── IV Rank (IBKR style): 30-day IV ÷ 30-day realised vol ──────────────────
    # The volatility risk premium — are options rich or cheap vs how the stock
    # actually moves? >1.2 = rich (market pricing more than realised; pre-catalyst
    # / fear premium); <0.8 = cheap (complacent / quiet).
    hv_pct = round(hv30 * 100, 1) if hv30 and hv30 > 0 else None
    iv_hv = None
    iv_state = None
    if atm_iv is not None and hv30 and hv30 > 0:
        iv_hv = round((atm_iv / 100) / hv30, 2)
        iv_state = "rich" if iv_hv >= 1.2 else "cheap" if iv_hv <= 0.8 else "fair"

    # ── Expected move (ATM straddle) to the nearest expiry ─────────────────────
    straddle = (_mid(atm_c) if atm_c is not None else 0) + (_mid(atm_p) if atm_p is not None else 0)
    exp_move_pct = round(straddle / spot * 100, 1) if spot > 0 and straddle > 0 else None
    exp_move_abs = round(straddle, 2) if straddle > 0 else None

    # ── Skew: OTM put IV − OTM call IV (positive = downside fear / put skew) ───
    otm_put = _nearest_row(nearest_puts, spot * (1 - _OTM_PCT))
    otm_call = _nearest_row(nearest_calls, spot * (1 + _OTM_PCT))
    skew = None
    if otm_put is not None and otm_call is not None:
        pv = float(otm_put["impliedVolatility"]); cv = float(otm_call["impliedVolatility"])
        if pv > 0 and cv > 0 and not (math.isnan(pv) or math.isnan(cv)):
            skew = round((pv - cv) * 100, 1)   # IV points

    # ── Unusual activity: today's volume vs resting open interest ──────────────
    tot_vol, tot_oi = call_vol + put_vol, call_oi + put_oi
    vol_oi = round(tot_vol / tot_oi, 2) if tot_oi > 0 else None
    if vol_oi is not None and vol_oi >= 0.5:
        ua_flag, ua_note = True, ("heavy" if vol_oi >= 1.0 else "elevated")
    else:
        ua_flag, ua_note = False, "normal"

    # ── Sentiment lean (context, contrarian-aware) ─────────────────────────────
    lean, tell_bits = "neutral", []
    call_heavy = pc_vol is not None and pc_vol < 0.7
    put_heavy = pc_vol is not None and pc_vol > 1.2
    call_demand = skew is not None and skew < -1
    fear = skew is not None and skew > 3
    if call_heavy:
        tell_bits.append(f"call-heavy flow (P/C vol {pc_vol})")
    if put_heavy:
        tell_bits.append(f"put-heavy flow (P/C vol {pc_vol})")
    if call_demand:
        tell_bits.append(f"call-skewed IV ({skew} pts → upside demand)")
    if fear:
        tell_bits.append(f"put-skewed IV (+{skew} pts → downside hedging)")
    if ua_flag:
        tell_bits.append(f"{ua_note} activity (vol/OI {vol_oi})")
    if iv_state == "rich":
        tell_bits.append(f"IV rich ({iv_hv}× realised — pricing a move)")
    elif iv_state == "cheap":
        tell_bits.append(f"IV cheap ({iv_hv}× realised — complacent)")
    if (call_heavy or call_demand) and not (put_heavy or fear):
        lean = "bullish"
    elif (put_heavy or fear) and not (call_heavy or call_demand):
        lean = "bearish"

    # ── ACI level: delta-adjusted-OI accumulation sentiment (snapshot, no history) ──
    tot_daoi = bull_daoi + bear_daoi
    aci_score = round((bull_daoi - bear_daoi) / tot_daoi, 2) if tot_daoi > 0 else None
    aci_label = "neutral"
    if aci_score is not None:
        aci_label = ("bullish" if aci_score > _ACI_THRESH
                     else "bearish" if aci_score < -_ACI_THRESH else "neutral")
    if aci_score is not None and aci_label != "neutral":
        tell_bits.append(f"delta-adj OI {aci_label} ({aci_score:+})")

    # ── OI-derived support / resistance (the "sentiment map" levels) ───────────
    res = sorted(((k, v) for k, v in call_oi_strikes.items() if k > spot), key=lambda kv: -kv[1])[:2]
    sup = sorted(((k, v) for k, v in put_oi_strikes.items() if k < spot), key=lambda kv: -kv[1])[:2]
    oi_resistance = [{"strike": round(k, 2), "oi": int(v)} for k, v in res]
    oi_support    = [{"strike": round(k, 2), "oi": int(v)} for k, v in sup]

    # ── Max pain (OI-weighted pin price for the near-dated chain) ──────────────
    max_pain = _max_pain(call_oi_strikes, put_oi_strikes)
    max_pain_dist = round((max_pain - spot) / spot * 100, 1) if max_pain and spot > 0 else None
    if max_pain is not None and max_pain_dist is not None:
        pull = "above" if max_pain_dist > 0 else "below"
        tell_bits.append(f"max pain ${max_pain:g} ({abs(max_pain_dist)}% {pull})")

    tell = "; ".join(tell_bits) if tell_bits else "balanced positioning, nothing unusual"

    return {
        "source":          "yfinance",
        "gex":             None,          # GEX/term-structure computed on the CBOE path
        "term_structure":  None,
        "nearest_expiry":  nearest,
        "dte":             dte,
        "expiries_used":   len(near),
        "atm_iv":          atm_iv,            # %  (None if unavailable)
        "hv":              hv_pct,            # 30d realised vol, %
        "iv_hv":           iv_hv,             # IBKR IV Rank = IV ÷ HV
        "iv_state":        iv_state,          # rich | fair | cheap
        "expected_move_pct": exp_move_pct,    # ± % of spot by nearest expiry
        "expected_move_abs": exp_move_abs,    # ± $ (ATM straddle)
        "skew":            skew,              # OTM put IV − OTM call IV, IV points
        "put_call_vol":    pc_vol,
        "put_call_oi":     pc_oi,
        "call_volume":     int(call_vol),
        "put_volume":      int(put_vol),
        "call_oi":         int(call_oi),
        "put_oi":          int(put_oi),
        "vol_oi_ratio":    vol_oi,
        "unusual_activity": ua_flag,
        "max_pain":        round(max_pain, 2) if max_pain else None,
        "max_pain_dist_pct": max_pain_dist,   # % from spot (pin gravity into expiry)
        "aci_score":       aci_score,         # delta-adj OI sentiment −1..+1 (LEVEL, no history)
        "aci_label":       aci_label,         # bullish | neutral | bearish
        "bull_daoi":       int(bull_daoi),    # call delta-adjusted OI
        "bear_daoi":       int(bear_daoi),    # put delta-adjusted OI
        "oi_resistance":   oi_resistance,     # call walls above price [{strike, oi}]
        "oi_support":      oi_support,        # put walls below price
        "lean":            lean,              # bullish | neutral | bearish (context)
        "tell":            tell,
    }


# ── Alpaca fallback (cloud IPs where yfinance is blocked) ──────────────────────
# Free "indicative" feed = quotes + volume, but NO open interest / IV / greeks.
# We invert IV from bid/ask mids (Black-Scholes) and return the OI-based metrics
# (P/C OI, max pain, ACI, OI walls) as null. Same output shape as the yfinance path.

_ALPACA_OPT_URL = "https://data.alpaca.markets/v1beta1/options/snapshots/{}"


def _compute_alpaca(symbol: str, spot: float, max_days: int, hv30: float | None = None,
                    min_dte: int = 7, target_dte: int = 30) -> dict | None:
    key, sec = os.getenv("ALPACA_API_KEY", ""), os.getenv("ALPACA_API_SECRET", "")
    if not key or not sec or spot <= 0:
        return None
    try:
        import httpx
    except Exception:
        return None
    from datetime import timedelta
    today = date.today()
    exp_lte = (today + timedelta(days=max_days)).isoformat()
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}
    url = _ALPACA_OPT_URL.format(symbol.upper())

    rows: list[dict] = []   # {type, strike, exp, dte, mid, vol}
    try:
        with httpx.Client(headers=headers) as client:
            token, pages = None, 0
            while pages < 12:
                params = {"feed": "indicative", "limit": "1000", "expiration_date_lte": exp_lte}
                if token:
                    params["page_token"] = token
                r = client.get(url, params=params, timeout=30)
                if r.status_code != 200:
                    break
                d = r.json()
                for csym, snap in (d.get("snapshots") or {}).items():
                    parsed = _parse_occ(csym)
                    if not parsed:
                        continue
                    exp, otype, strike = parsed
                    dte = (exp - today).days
                    if dte < 0 or dte > max_days:
                        continue
                    q = snap.get("latestQuote") or {}
                    bid, ask = float(q.get("bp", 0) or 0), float(q.get("ap", 0) or 0)
                    mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else 0.0
                    vol = float((snap.get("dailyBar") or {}).get("v", 0) or 0)
                    rows.append({"type": otype, "strike": strike, "exp": exp, "dte": dte, "mid": mid, "vol": vol})
                token = d.get("next_page_token")
                pages += 1
                if not token:
                    break
    except Exception as e:
        logger.debug("options(alpaca): fetch failed for %s: %s", symbol, e)
        return None
    if not rows:
        return None

    # Skip the noisy current-week weeklies (< min_dte); anchor to the expiry
    # closest to target_dte (~30d) for IV / expected move / skew.
    rows = [r for r in rows if r["dte"] >= min_dte] or rows
    exps = sorted({r["exp"] for r in rows})
    nearest = min(exps, key=lambda e: abs((e - today).days - target_dte))
    dte = max((nearest - today).days, 0)
    T = max(dte, 1) / 365.0
    calls = [r for r in rows if r["type"] == "call"]
    puts = [r for r in rows if r["type"] == "put"]
    call_vol = sum(r["vol"] for r in calls)
    put_vol = sum(r["vol"] for r in puts)
    pc_vol = round(put_vol / call_vol, 2) if call_vol > 0 else None

    near_calls = [r for r in calls if r["exp"] == nearest and r["mid"] > 0]
    near_puts = [r for r in puts if r["exp"] == nearest and r["mid"] > 0]

    def _iv_near(cands: list[dict], target: float, otype: str):
        cands = [r for r in cands if r["mid"] > 0]
        if not cands:
            return None
        row = min(cands, key=lambda r: abs(r["strike"] - target))
        return _implied_vol(otype, row["mid"], spot, row["strike"], T)

    atm_c_iv = _iv_near(near_calls, spot, "call")
    atm_p_iv = _iv_near(near_puts, spot, "put")
    ivs = [v for v in (atm_c_iv, atm_p_iv) if v]
    atm_iv = round(sum(ivs) / len(ivs) * 100, 1) if ivs else None

    hv_pct = round(hv30 * 100, 1) if hv30 and hv30 > 0 else None
    iv_hv = round((atm_iv / 100) / hv30, 2) if (atm_iv and hv30 and hv30 > 0) else None
    iv_state = ("rich" if iv_hv >= 1.2 else "cheap" if iv_hv <= 0.8 else "fair") if iv_hv else None

    atm_c = min(near_calls, key=lambda r: abs(r["strike"] - spot)) if near_calls else None
    atm_p = min(near_puts, key=lambda r: abs(r["strike"] - spot)) if near_puts else None
    straddle = (atm_c["mid"] if atm_c else 0) + (atm_p["mid"] if atm_p else 0)
    exp_move_pct = round(straddle / spot * 100, 1) if straddle > 0 else None
    exp_move_abs = round(straddle, 2) if straddle > 0 else None

    otm_put_iv = _iv_near(near_puts, spot * (1 - _OTM_PCT), "put")
    otm_call_iv = _iv_near(near_calls, spot * (1 + _OTM_PCT), "call")
    skew = round((otm_put_iv - otm_call_iv) * 100, 1) if (otm_put_iv and otm_call_iv) else None

    lean, tell_bits = "neutral", []
    call_heavy = pc_vol is not None and pc_vol < 0.7
    put_heavy = pc_vol is not None and pc_vol > 1.2
    call_demand = skew is not None and skew < -1
    fear = skew is not None and skew > 3
    if call_heavy:
        tell_bits.append(f"call-heavy flow (P/C vol {pc_vol})")
    if put_heavy:
        tell_bits.append(f"put-heavy flow (P/C vol {pc_vol})")
    if call_demand:
        tell_bits.append(f"call-skewed IV ({skew} pts → upside demand)")
    if fear:
        tell_bits.append(f"put-skewed IV (+{skew} pts → downside hedging)")
    if iv_state == "rich":
        tell_bits.append(f"IV rich ({iv_hv}× realised)")
    elif iv_state == "cheap":
        tell_bits.append(f"IV cheap ({iv_hv}× realised)")
    if (call_heavy or call_demand) and not (put_heavy or fear):
        lean = "bullish"
    elif (put_heavy or fear) and not (call_heavy or call_demand):
        lean = "bearish"
    tell_bits.append("OI metrics N/A (free feed)")
    tell = "; ".join(tell_bits) if tell_bits else "balanced positioning, nothing unusual"

    return {
        "source":          "alpaca",
        "gex":             None,          # needs OI + gamma; CBOE-path only
        "term_structure":  None,
        "nearest_expiry":  nearest.isoformat(),
        "dte":             dte,
        "expiries_used":   len(exps),
        "atm_iv":          atm_iv,
        "hv":              hv_pct,
        "iv_hv":           iv_hv,
        "iv_state":        iv_state,
        "expected_move_pct": exp_move_pct,
        "expected_move_abs": exp_move_abs,
        "skew":            skew,
        "put_call_vol":    pc_vol,
        "put_call_oi":     None,          # OI not in Alpaca free feed
        "call_volume":     int(call_vol),
        "put_volume":      int(put_vol),
        "call_oi":         0,
        "put_oi":          0,
        "vol_oi_ratio":    None,
        "unusual_activity": False,
        "max_pain":        None,          # needs OI
        "max_pain_dist_pct": None,
        "aci_score":       None,          # needs OI
        "aci_label":       "neutral",
        "bull_daoi":       0,
        "bear_daoi":       0,
        "oi_resistance":   [],            # needs OI
        "oi_support":      [],
        "lean":            lean,
        "tell":            tell,
    }


# ── CBOE delayed-quotes CDN (FULL chain incl. OI / IV / greeks, free, no key) ───
# Datacenter-friendly (works on cloud IPs where yfinance is blocked), ~15-min
# delayed. This is the preferred source: it gives everything (OI + IV + greeks),
# so no Black-Scholes inversion is needed and all OI metrics populate.

_CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{}.json"
_CBOE_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Accept": "application/json"}


def _compute_cboe(symbol: str, spot: float, max_days: int, hv30: float | None = None,
                  min_dte: int = 7, target_dte: int = 30) -> dict | None:
    if spot <= 0:
        return None
    try:
        import httpx
        with httpx.Client(headers=_CBOE_UA) as client:
            r = client.get(_CBOE_URL.format(symbol.upper()), timeout=20)
        if r.status_code != 200:
            return None
        data = (r.json().get("data") or {}).get("options") or []
    except Exception as e:
        logger.debug("options(cboe): fetch failed for %s: %s", symbol, e)
        return None
    if not data:
        return None

    today = date.today()
    contracts = []
    for o in data:
        p = _parse_occ(o.get("option", ""))
        if not p:
            continue
        exp, otype, strike = p
        dte = (exp - today).days
        if dte < 0 or dte > max_days:
            continue
        bid, ask = float(o.get("bid", 0) or 0), float(o.get("ask", 0) or 0)
        mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else 0.0
        contracts.append({
            "type": otype, "strike": strike, "exp": exp, "dte": dte, "mid": mid,
            "iv": float(o.get("iv", 0) or 0), "oi": float(o.get("open_interest", 0) or 0),
            "vol": float(o.get("volume", 0) or 0), "delta": float(o.get("delta", 0) or 0),
        })
    if not contracts:
        return None

    # Swing-tuned expiry selection: skip <min_dte; anchor near target_dte (~30d).
    usable = [c for c in contracts if c["dte"] >= min_dte] or contracts
    exps = sorted({c["exp"] for c in usable})
    anchor = min(exps, key=lambda e: abs((e - today).days - target_dte))
    near_exps = set(sorted(exps, key=lambda e: abs((e - today).days - (anchor - today).days))[:_MAX_EXPIRIES])
    agg = [c for c in usable if c["exp"] in near_exps]
    dte = max((anchor - today).days, 0)

    calls = [c for c in agg if c["type"] == "call"]
    puts = [c for c in agg if c["type"] == "put"]
    call_vol = sum(c["vol"] for c in calls); put_vol = sum(c["vol"] for c in puts)
    call_oi = sum(c["oi"] for c in calls); put_oi = sum(c["oi"] for c in puts)
    pc_vol = round(put_vol / call_vol, 2) if call_vol > 0 else None
    pc_oi = round(put_oi / call_oi, 2) if call_oi > 0 else None

    call_oi_strikes: dict[float, float] = {}
    put_oi_strikes: dict[float, float] = {}
    bull_daoi = bear_daoi = 0.0
    for c in calls:
        call_oi_strikes[c["strike"]] = call_oi_strikes.get(c["strike"], 0.0) + c["oi"]
        bull_daoi += c["oi"] * abs(c["delta"])    # CBOE provides delta directly
    for p in puts:
        put_oi_strikes[p["strike"]] = put_oi_strikes.get(p["strike"], 0.0) + p["oi"]
        bear_daoi += p["oi"] * abs(p["delta"])

    anc_calls = [c for c in calls if c["exp"] == anchor]
    anc_puts = [c for c in puts if c["exp"] == anchor]

    def _near(rows, tgt, iv_only=False):
        rows = [r for r in rows if (r["iv"] > 0 if iv_only else True)]
        return min(rows, key=lambda r: abs(r["strike"] - tgt)) if rows else None

    atm_c, atm_p = _near(anc_calls, spot), _near(anc_puts, spot)
    ivs = [x["iv"] for x in (atm_c, atm_p) if x and x["iv"] > 0]
    atm_iv = round(sum(ivs) / len(ivs) * 100, 1) if ivs else None

    hv_pct = round(hv30 * 100, 1) if hv30 and hv30 > 0 else None
    iv_hv = round((atm_iv / 100) / hv30, 2) if (atm_iv and hv30 and hv30 > 0) else None
    iv_state = ("rich" if iv_hv >= 1.2 else "cheap" if iv_hv <= 0.8 else "fair") if iv_hv else None

    straddle = (atm_c["mid"] if atm_c else 0) + (atm_p["mid"] if atm_p else 0)
    exp_move_pct = round(straddle / spot * 100, 1) if straddle > 0 else None
    exp_move_abs = round(straddle, 2) if straddle > 0 else None

    otm_p = _near(anc_puts, spot * (1 - _OTM_PCT), iv_only=True)
    otm_c = _near(anc_calls, spot * (1 + _OTM_PCT), iv_only=True)
    skew = round((otm_p["iv"] - otm_c["iv"]) * 100, 1) if (otm_p and otm_c) else None

    tot_vol, tot_oi = call_vol + put_vol, call_oi + put_oi
    vol_oi = round(tot_vol / tot_oi, 2) if tot_oi > 0 else None
    ua_flag = vol_oi is not None and vol_oi >= 0.5
    ua_note = ("heavy" if (vol_oi or 0) >= 1.0 else "elevated") if ua_flag else "normal"

    tot_daoi = bull_daoi + bear_daoi
    aci_score = round((bull_daoi - bear_daoi) / tot_daoi, 2) if tot_daoi > 0 else None
    aci_label = ("bullish" if (aci_score or 0) > _ACI_THRESH else "bearish"
                 if (aci_score or 0) < -_ACI_THRESH else "neutral") if aci_score is not None else "neutral"

    res = sorted(((k, v) for k, v in call_oi_strikes.items() if k > spot), key=lambda kv: -kv[1])[:2]
    sup = sorted(((k, v) for k, v in put_oi_strikes.items() if k < spot), key=lambda kv: -kv[1])[:2]
    oi_resistance = [{"strike": round(k, 2), "oi": int(v)} for k, v in res]
    oi_support = [{"strike": round(k, 2), "oi": int(v)} for k, v in sup]

    max_pain = _max_pain(call_oi_strikes, put_oi_strikes)
    max_pain_dist = round((max_pain - spot) / spot * 100, 1) if max_pain and spot > 0 else None

    # Gamma exposure + IV term structure (use the full chain incl. weeklies — gamma
    # peaks near expiry and term structure needs the front week).
    gex = _gex(contracts, spot)
    term = _term_structure(contracts, spot)

    lean, tell_bits = "neutral", []
    call_heavy = pc_vol is not None and pc_vol < 0.7
    put_heavy = pc_vol is not None and pc_vol > 1.2
    call_demand = skew is not None and skew < -1
    fear = skew is not None and skew > 3
    if call_heavy: tell_bits.append(f"call-heavy flow (P/C vol {pc_vol})")
    if put_heavy: tell_bits.append(f"put-heavy flow (P/C vol {pc_vol})")
    if call_demand: tell_bits.append(f"call-skewed IV ({skew} pts → upside demand)")
    if fear: tell_bits.append(f"put-skewed IV (+{skew} pts → downside hedging)")
    if ua_flag: tell_bits.append(f"{ua_note} activity (vol/OI {vol_oi})")
    if iv_state == "rich": tell_bits.append(f"IV rich ({iv_hv}× realised — pricing a move)")
    elif iv_state == "cheap": tell_bits.append(f"IV cheap ({iv_hv}× realised — complacent)")
    if (call_heavy or call_demand) and not (put_heavy or fear): lean = "bullish"
    elif (put_heavy or fear) and not (call_heavy or call_demand): lean = "bearish"
    if aci_score is not None and aci_label != "neutral":
        tell_bits.append(f"delta-adj OI {aci_label} ({aci_score:+})")
    if max_pain is not None and max_pain_dist is not None:
        tell_bits.append(f"max pain ${max_pain:g} ({abs(max_pain_dist)}% {'above' if max_pain_dist > 0 else 'below'})")
    if gex:
        tell_bits.append(f"{gex['regime']} dealer gamma" + (f" (flip ${gex['flip']:g})" if gex.get('flip') else ""))
    if term and term["state"] != "flat":
        tell_bits.append(f"IV {term['state']} ({term['front_iv']}%→{term['back_iv']}%)")
    tell = "; ".join(tell_bits) if tell_bits else "balanced positioning, nothing unusual"

    return {
        "source":          "cboe",
        "gex":             gex,
        "term_structure":  term,
        "nearest_expiry":  anchor.isoformat(),
        "dte":             dte,
        "expiries_used":   len(near_exps),
        "atm_iv":          atm_iv,
        "hv":              hv_pct,
        "iv_hv":           iv_hv,
        "iv_state":        iv_state,
        "expected_move_pct": exp_move_pct,
        "expected_move_abs": exp_move_abs,
        "skew":            skew,
        "put_call_vol":    pc_vol,
        "put_call_oi":     pc_oi,
        "call_volume":     int(call_vol),
        "put_volume":      int(put_vol),
        "call_oi":         int(call_oi),
        "put_oi":          int(put_oi),
        "vol_oi_ratio":    vol_oi,
        "unusual_activity": ua_flag,
        "max_pain":        round(max_pain, 2) if max_pain else None,
        "max_pain_dist_pct": max_pain_dist,
        "aci_score":       aci_score,
        "aci_label":       aci_label,
        "bull_daoi":       int(bull_daoi),
        "bear_daoi":       int(bear_daoi),
        "oi_resistance":   oi_resistance,
        "oi_support":      oi_support,
        "lean":            lean,
        "tell":            tell,
    }
