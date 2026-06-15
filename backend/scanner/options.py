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

Data source: yfinance option chains (free, no keys, includes IV/OI/volume). The
OHLCV fetcher uses Alpaca on cloud IPs because yfinance *bars* get blocked there;
options endpoints differ, but if yfinance options prove unreliable on Render the
chain fetch can be swapped for Alpaca's /v1beta1/options/snapshots (computing IV
via Black-Scholes from mids, since the free feed omits greeks). The metrics layer
below is source-agnostic.

Like the Fibonacci grid, this is a CONFLUENCE / CONTEXT layer — NOT a P Score input.
"""
from __future__ import annotations

import logging
import math
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


def compute_options(symbol: str, spot: float, max_days: int = 45,
                    hv30: float | None = None) -> dict | None:
    """Compute the leading-options snapshot for ``symbol`` at the given ``spot``.

    ``hv30`` is the 30-day annualised realised (historical) volatility as a
    fraction (e.g. 0.85 = 85%). When supplied, the snapshot adds IBKR's IV Rank
    (30-day IV ÷ 30-day HV) — the volatility risk premium that tells you whether
    options are rich or cheap relative to how the stock is actually moving.

    Returns a JSON-serialisable dict, or None if no usable chain is available.
    """
    now = time.time()
    cached = _CACHE.get(symbol)
    if cached and now - cached[0] < _TTL_SEC:
        return cached[1]

    result = _compute(symbol, spot, max_days, hv30)
    _CACHE[symbol] = (now, result)
    return result


def _compute(symbol: str, spot: float, max_days: int, hv30: float | None = None) -> dict | None:
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

    near = [e for e in exps if 0 <= _dte(e) <= max_days] or exps[:1]
    near = near[:_MAX_EXPIRIES]
    nearest = near[0]
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
