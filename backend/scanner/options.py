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


def compute_options(symbol: str, spot: float, max_days: int = 45) -> dict | None:
    """Compute the leading-options snapshot for ``symbol`` at the given ``spot``.

    Returns a JSON-serialisable dict, or None if no usable chain is available.
    """
    now = time.time()
    cached = _CACHE.get(symbol)
    if cached and now - cached[0] < _TTL_SEC:
        return cached[1]

    result = _compute(symbol, spot, max_days)
    _CACHE[symbol] = (now, result)
    return result


def _compute(symbol: str, spot: float, max_days: int) -> dict | None:
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
    nearest_calls = nearest_puts = None
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
    if (call_heavy or call_demand) and not (put_heavy or fear):
        lean = "bullish"
    elif (put_heavy or fear) and not (call_heavy or call_demand):
        lean = "bearish"

    tell = "; ".join(tell_bits) if tell_bits else "balanced positioning, nothing unusual"

    return {
        "source":          "yfinance",
        "nearest_expiry":  nearest,
        "dte":             dte,
        "expiries_used":   len(near),
        "atm_iv":          atm_iv,            # %  (None if unavailable)
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
        "lean":            lean,              # bullish | neutral | bearish (context)
        "tell":            tell,
    }
