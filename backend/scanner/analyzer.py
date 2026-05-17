"""Single-symbol deep analysis — powers the /analyze page.

Produces every signal the qmag-platform knows about for one stock:
  - All 6 pattern detectors (EP, TB, PP, PULL, FBD, WYS)
  - RSI, MACD, ADX
  - MA stack (EMA21/50/SMA150)
  - Weinstein stage, A/D net, ICS, RVOL
  - Signal checklist (9 items)
  - Early warnings (bull exhaustion, overextension, volume dry-up, momentum fading)
  - Score breakdown (what is helping/hurting composite)
  - Multi-timeframe alignment (daily / weekly / monthly) — resampled from daily bars,
    no extra API calls required
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from .fetcher import fetch_ohlcv
from .patterns import (
    detect_ep, detect_tb, detect_pp, detect_pull, detect_fbd, detect_wys,
    weinstein_stage, ad_days, overextension_penalty,
    relative_volume, institutional_composite_score, bull_exhaustion_warning,
)
from .rs_rank import rs_score, rs_label

logger = logging.getLogger(__name__)


# ── Technical indicator helpers ───────────────────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram) as Series."""
    ema_fast    = close.ewm(span=fast, adjust=False).mean()
    ema_slow    = close.ewm(span=slow, adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def _adx(df: pd.DataFrame, period: int = 14) -> float:
    """Wilder's Average Directional Index (0-100). >25 = trending."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"]

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm  = plus_dm.where(plus_dm  > minus_dm, 0.0)
    minus_dm = minus_dm.where(minus_dm > plus_dm,  0.0)

    atr      = tr.ewm(span=period, adjust=False).mean()
    plus_di  = 100 * plus_dm.ewm(span=period, adjust=False).mean()  / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_s    = dx.ewm(span=period, adjust=False).mean()

    val = float(adx_s.iloc[-1])
    return round(val, 1) if not np.isnan(val) else 0.0


# ── MA stack analysis ─────────────────────────────────────────────────────────

def _ma_stack(close: pd.Series, ema21: pd.Series, ema50: pd.Series, sma150: pd.Series) -> dict:
    curr = float(close.iloc[-1])
    e21  = float(ema21.iloc[-1])
    e50  = float(ema50.iloc[-1])
    s150 = float(sma150.iloc[-1]) if not pd.isna(sma150.iloc[-1]) else None

    e21_rising = float(ema21.iloc[-1]) > float(ema21.iloc[-11]) if len(ema21) > 11 else False
    e50_rising = float(ema50.iloc[-1]) > float(ema50.iloc[-11]) if len(ema50) > 11 else False

    above_e21  = curr > e21
    above_e50  = curr > e50
    e21_gt_e50 = e21  > e50

    if above_e21 and above_e50 and e21_gt_e50 and e21_rising and e50_rising:
        if s150 and curr > s150:
            stack  = "full_bull"
            detail = "Price > EMA21 > EMA50 > SMA150 — all rising ✓"
        else:
            stack  = "partial_bull"
            detail = "Price > EMA21 > EMA50, both rising (below 30-week MA)"
    elif above_e21 and e21_gt_e50:
        stack  = "partial_bull"
        detail = "Price > EMA21 > EMA50 (MAs not all rising)"
    elif not above_e21 and not above_e50:
        stack  = "bear"
        detail = "Price below EMA21 and EMA50 — bearish structure"
    else:
        stack  = "mixed"
        detail = "Mixed MA alignment — wait for clarity"

    return {
        "stack":             stack,
        "detail":            detail,
        "price_vs_ema21_pct": round((curr - e21) / e21 * 100, 1) if e21 > 0 else 0.0,
        "price_vs_ema50_pct": round((curr - e50) / e50 * 100, 1) if e50 > 0 else 0.0,
        "ema21_rising":      e21_rising,
        "ema50_rising":      e50_rising,
        "ema21":             round(e21, 2),
        "ema50":             round(e50, 2),
        "sma150":            round(s150, 2) if s150 else None,
    }


# ── Signal checklist ──────────────────────────────────────────────────────────

def _checklist(
    stage: int, rsi_val: float, adx_val: float, macd_hist: float,
    ma: dict, rvol_val: float, ad: int, isc: float, rs_raw: float,
) -> list[dict]:
    """9-item signal checklist. Each item: {label, status, detail}.
    status: "pass" | "warn" | "fail" | "neutral"
    """
    items = []

    # 1 — MA Stack
    s = {"full_bull": "pass", "partial_bull": "warn", "mixed": "warn", "bear": "fail"}.get(ma["stack"], "neutral")
    items.append({"label": "MA Stack", "status": s, "detail": ma["detail"]})

    # 2 — Weinstein Stage
    stage_labels   = {1: "S1 Basing — wait for Stage 2", 2: "S2 Advancing — the only stage to trade",
                      3: "S3 Topping — avoid new longs", 4: "S4 Declining — no longs"}
    stage_statuses = {1: "warn", 2: "pass", 3: "fail", 4: "fail"}
    items.append({
        "label":  "Weinstein Stage",
        "status": stage_statuses.get(stage, "neutral"),
        "detail": stage_labels.get(stage, "Insufficient data (<150 bars)"),
    })

    # 3 — RSI
    if 40 <= rsi_val <= 65:
        items.append({"label": "RSI", "status": "pass",    "detail": f"RSI {rsi_val:.0f} — healthy, room to run"})
    elif rsi_val > 80:
        items.append({"label": "RSI", "status": "fail",    "detail": f"RSI {rsi_val:.0f} — overbought, high reversal risk"})
    elif rsi_val > 65:
        items.append({"label": "RSI", "status": "warn",    "detail": f"RSI {rsi_val:.0f} — getting extended"})
    elif rsi_val < 30:
        items.append({"label": "RSI", "status": "warn",    "detail": f"RSI {rsi_val:.0f} — oversold, possible bounce"})
    else:
        items.append({"label": "RSI", "status": "warn",    "detail": f"RSI {rsi_val:.0f} — below ideal entry zone"})

    # 4 — MACD
    if macd_hist > 0:
        items.append({"label": "MACD", "status": "pass",   "detail": "Histogram positive — bullish momentum"})
    elif macd_hist < -0.001:
        items.append({"label": "MACD", "status": "fail",   "detail": "Histogram negative — bearish momentum"})
    else:
        items.append({"label": "MACD", "status": "warn",   "detail": "Near zero — neutral momentum"})

    # 5 — ADX
    if adx_val >= 30:
        items.append({"label": "ADX Trend", "status": "pass",  "detail": f"ADX {adx_val:.0f} — strong trend, momentum behind move"})
    elif adx_val >= 20:
        items.append({"label": "ADX Trend", "status": "warn",  "detail": f"ADX {adx_val:.0f} — developing trend"})
    else:
        items.append({"label": "ADX Trend", "status": "fail",  "detail": f"ADX {adx_val:.0f} — no trend, choppy"})

    # 6 — RVOL
    if rvol_val >= 2.0:
        items.append({"label": "Rel. Volume", "status": "pass", "detail": f"{rvol_val:.1f}× avg — surge, institutional participation"})
    elif rvol_val >= 1.2:
        items.append({"label": "Rel. Volume", "status": "pass", "detail": f"{rvol_val:.1f}× avg — above average"})
    elif rvol_val >= 0.7:
        items.append({"label": "Rel. Volume", "status": "warn", "detail": f"{rvol_val:.1f}× avg — below average, low conviction"})
    else:
        items.append({"label": "Rel. Volume", "status": "fail", "detail": f"{rvol_val:.1f}× avg — very low, avoid breakouts here"})

    # 7 — A/D Net
    if ad >= 5:
        items.append({"label": "A/D Net", "status": "pass",    "detail": f"+{ad} accumulation days — institutions buying"})
    elif ad > 0:
        items.append({"label": "A/D Net", "status": "pass",    "detail": f"+{ad} mild accumulation"})
    elif ad == 0:
        items.append({"label": "A/D Net", "status": "neutral", "detail": "0 — balanced buying and selling"})
    else:
        items.append({"label": "A/D Net", "status": "fail",    "detail": f"{ad} distribution days — institutions selling"})

    # 8 — ICS
    if isc >= 75:
        items.append({"label": "ICS", "status": "pass",        "detail": f"ICS {isc:.0f} — strong institutional accumulation"})
    elif isc >= 40:
        items.append({"label": "ICS", "status": "warn",        "detail": f"ICS {isc:.0f} — mixed institutional signals"})
    else:
        items.append({"label": "ICS", "status": "fail",        "detail": f"ICS {isc:.0f} — institutional distribution"})

    # 9 — RS vs SPY
    if rs_raw >= 75:
        items.append({"label": "RS vs SPY", "status": "pass",  "detail": f"RS {rs_raw:.0f} — clear market leader"})
    elif rs_raw >= 50:
        items.append({"label": "RS vs SPY", "status": "warn",  "detail": f"RS {rs_raw:.0f} — matching SPY, not leading"})
    else:
        items.append({"label": "RS vs SPY", "status": "fail",  "detail": f"RS {rs_raw:.0f} — underperforming SPY"})

    return items


# ── Early warnings ────────────────────────────────────────────────────────────

def _warnings(df: pd.DataFrame, exhaustion_str: str | None, penalty: float) -> list[dict]:
    """Detect early warnings. Each: {name, severity, detail}.
    severity: "info" | "warning" | "critical"
    """
    w: list[dict] = []

    if exhaustion_str:
        w.append({"name": "Bull Exhaustion", "severity": "warning", "detail": exhaustion_str})

    if penalty >= 0.10:
        w.append({"name": "Overextended", "severity": "critical",
                  "detail": f"RSI or price >8% above EMA21 — confidence docked -{penalty*100:.0f}pts"})
    elif penalty > 0:
        w.append({"name": "Mildly Extended", "severity": "info",
                  "detail": f"Minor overextension — confidence docked -{penalty*100:.0f}pts"})

    volume = df["volume"]
    if len(volume) >= 22:
        avg_20 = float(volume.iloc[-21:-1].mean())
        curr_v = float(volume.iloc[-1])
        if avg_20 > 0 and curr_v < avg_20 * 0.40:
            w.append({"name": "Volume Dry-Up", "severity": "info",
                      "detail": f"{curr_v/avg_20:.0%} of 20-day avg — contraction may precede breakout"})

    # Momentum fading: MACD histogram shrinking for 3 bars while positive
    close = df["close"]
    ema12     = close.ewm(span=12, adjust=False).mean()
    ema26     = close.ewm(span=26, adjust=False).mean()
    hist_s    = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    if len(hist_s) >= 4:
        h = [float(hist_s.iloc[-i]) for i in range(1, 5)]
        if h[0] > 0 and h[1] > h[0] and h[2] > h[1]:
            w.append({"name": "Momentum Fading", "severity": "warning",
                      "detail": "MACD histogram contracting 3+ bars — buying pressure easing"})
        elif h[0] < 0 and h[1] < h[0] and h[2] < h[1]:
            w.append({"name": "Bear Momentum Fading", "severity": "info",
                      "detail": "MACD histogram contracting on bearish side — selling pressure easing"})

    return w


# ── Multi-timeframe resampling ────────────────────────────────────────────────

def _resample_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly bars (week-end). No extra API call needed."""
    return (
        df.resample("W")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )


def _resample_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to monthly bars. No extra API call needed."""
    try:
        rule = "ME"  # pandas ≥ 2.2
        return (
            df.resample(rule)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna()
        )
    except Exception:
        rule = "M"
        return (
            df.resample(rule)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna()
        )


def _tf_signals(df: pd.DataFrame, label: str) -> dict:
    """Compute key trend signals for a single timeframe.

    Key MA conventions:
      Daily   → SMA 150  (≈ 30-week proxy on daily bars)
      Weekly  → SMA 30   (exact Weinstein 30-week MA)
      Monthly → SMA 12   (12-month trend MA)
    """
    if len(df) < 14:
        return {"label": label, "bars": len(df), "direction": "neutral", "insufficient": True}

    close = df["close"]
    curr  = float(close.iloc[-1])

    # RSI
    rsi_s   = _rsi(close, 14)
    rsi_val = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else 50.0

    # MACD histogram
    _, _, hist_s  = _macd(close)
    macd_hist_val = float(hist_s.iloc[-1]) if not pd.isna(hist_s.iloc[-1]) else 0.0

    # Short/long EMAs — span sizes scaled to timeframe bar density
    fast_span, slow_span = (10, 21) if label != "Daily" else (21, 50)
    ema_f = float(close.ewm(span=fast_span, adjust=False).mean().iloc[-1])
    ema_s = float(close.ewm(span=slow_span, adjust=False).mean().iloc[-1])

    # Key MA (stage proxy)
    ma_periods = {"Daily": 150, "Weekly": 30, "Monthly": 12}
    ma_p     = ma_periods.get(label, 30)
    key_ma_val: float | None = None
    stage    = 0
    ma_label = f"SMA{ma_p}"

    if len(close) >= ma_p:
        key_ma_s  = close.rolling(ma_p).mean()
        key_ma_val = float(key_ma_s.iloc[-1])
        lookback  = min(5, len(key_ma_s) - 1)
        prev_ma   = float(key_ma_s.iloc[-lookback - 1])
        slope_pct = (key_ma_val - prev_ma) / prev_ma * 100 if prev_ma > 0 else 0.0
        above     = curr > key_ma_val
        if   slope_pct >  0.3 and above:  stage = 2
        elif slope_pct < -0.3 and not above: stage = 4
        elif above:                         stage = 3
        else:                               stage = 1

    # Bullish signal count (0–5): RSI > 50, MACD +, price > fast EMA, fast > slow EMA, Stage 2
    bull_count = sum([
        rsi_val > 50,
        macd_hist_val > 0,
        curr > ema_f,
        ema_f > ema_s,
        stage == 2,
    ])
    direction = "bullish" if bull_count >= 4 else "bearish" if bull_count <= 1 else "neutral"

    return {
        "label":            label,
        "bars":             len(df),
        "direction":        direction,
        "stage":            stage,
        "rsi":              round(rsi_val, 1),
        "macd":             "bullish" if macd_hist_val > 0 else "bearish",
        "ema_fast":         round(ema_f, 2),
        "ema_slow":         round(ema_s, 2),
        "price_vs_ema_pct": round((curr - ema_f) / ema_f * 100, 1) if ema_f > 0 else 0.0,
        "key_ma":           round(key_ma_val, 2) if key_ma_val is not None else None,
        "key_ma_label":     ma_label,
    }


def _mtf_alignment(daily: dict, weekly: dict, monthly: dict) -> dict:
    """Summarise multi-timeframe alignment.

    Score: +1 per bullish TF, -1 per bearish TF → range [-3, +3].
    Full alignment (±3) = highest conviction.
    """
    dirs  = [d.get("direction", "neutral") for d in (daily, weekly, monthly)]
    bull  = dirs.count("bullish")
    bear  = dirs.count("bearish")

    if   bull == 3: alignment, score, label = "full_bull",   3, "All 3 timeframes bullish — maximum conviction"
    elif bull == 2: alignment, score, label = "mostly_bull", 2, "2 of 3 timeframes bullish — good alignment"
    elif bear == 3: alignment, score, label = "full_bear",  -3, "All 3 timeframes bearish — avoid longs"
    elif bear == 2: alignment, score, label = "mostly_bear",-2, "2 of 3 bearish — high risk for longs"
    else:           alignment, score, label = "mixed",       0, "Mixed signals across timeframes — wait for clarity"

    return {
        "alignment": alignment,
        "score":     score,
        "label":     label,
        "daily":     daily,
        "weekly":    weekly,
        "monthly":   monthly,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze_symbol(symbol: str, spy_close: pd.Series | None = None) -> dict[str, Any] | None:
    """Run full analysis for a single symbol.

    Returns a rich dict with every signal the platform computes, suitable for
    direct JSON serialisation and rendering on the /analyze page.
    Returns None if data cannot be fetched or is too short.
    """
    df = fetch_ohlcv(symbol, period_days=730)   # ~2 years daily OHLCV
    if df is None or len(df) < 60:
        return None

    close  = df["close"]
    volume = df["volume"]
    price  = float(close.iloc[-1])
    prev   = float(close.iloc[-2]) if len(close) >= 2 else price
    pct_change = round((price - prev) / prev * 100, 2) if prev > 0 else 0.0

    # ── RS score ──────────────────────────────────────────────────────────────
    rs_raw_val, rs_lbl = 50.0, "RS Average"
    if spy_close is not None:
        try:
            rs_data    = rs_score(close, spy_close)
            rs_raw_val = round(float(rs_data["rs_raw"]), 1)
            rs_lbl     = rs_label(rs_raw_val)
        except Exception:
            pass

    # ── Enrichment signals (computed once) ────────────────────────────────────
    stage     = weinstein_stage(df)
    ad        = ad_days(df)
    rvol_val  = relative_volume(df)
    isc       = institutional_composite_score(df)
    penalty   = overextension_penalty(df)
    exhaustion = bull_exhaustion_warning(df)

    # ── Technical indicators ──────────────────────────────────────────────────
    ema21  = close.ewm(span=21, adjust=False).mean()
    ema50  = close.ewm(span=50, adjust=False).mean()
    sma150 = close.rolling(150).mean()

    rsi_series  = _rsi(close, 14)
    rsi_val     = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 55.0

    _ml, _sl, hist_s = _macd(close)
    macd_hist  = float(hist_s.iloc[-1])   if not pd.isna(hist_s.iloc[-1])  else 0.0
    macd_prev  = float(hist_s.iloc[-2])   if len(hist_s) >= 2 and not pd.isna(hist_s.iloc[-2]) else macd_hist
    macd_direction = "bullish" if macd_hist > 0 else "bearish"
    macd_expanding = (macd_hist > 0 and macd_hist > macd_prev) or (macd_hist < 0 and macd_hist < macd_prev)

    adx_val = _adx(df)

    avg_vol_50 = float(volume.iloc[-51:-1].mean()) if len(volume) >= 52 else float(volume.mean())
    vol_ratio  = round(float(volume.iloc[-1]) / avg_vol_50, 2) if avg_vol_50 > 0 else 1.0

    ma_info = _ma_stack(close, ema21, ema50, sma150)

    # ── Run all detectors (no RS/price filters — show everything) ─────────────
    active_setups: list = []
    for detect in [detect_ep, detect_tb, detect_wys, detect_pp, detect_pull, detect_fbd]:
        try:
            hit = detect(df, max_base_bars=500) if detect == detect_tb else detect(df)
            if hit is None:
                continue
            hit.symbol        = symbol
            hit.rs_score      = rs_raw_val
            hit.rs_label      = rs_lbl
            hit.weinstein_stage = stage
            hit.ad_net        = ad
            hit.rvol          = rvol_val
            hit.isc_score     = isc
            if penalty > 0:
                hit.confidence = round(max(0.30, hit.confidence - penalty), 2)
                hit.meta["overextension_penalty"] = penalty
            active_setups.append(hit)
        except Exception as e:
            logger.debug("Analyzer detector %s error on %s: %s", detect.__name__, symbol, e)

    # ── Checklist + warnings ──────────────────────────────────────────────────
    checklist_items = _checklist(stage, rsi_val, adx_val, macd_hist, ma_info, rvol_val, ad, isc, rs_raw_val)
    warning_items   = _warnings(df, exhaustion, penalty)

    # ── Best setup + composite score ──────────────────────────────────────────
    best = max(active_setups, key=lambda s: s.composite_score) if active_setups else None

    if best:
        comp_score = best.composite_score
        grade_val  = best.grade
        pat_pts    = round(best.quality_score * 60, 1)
        pat_label  = best.setup_type
    else:
        # No pattern firing — compute a symbol-level score with quality_score=0.50
        base       = 0.50 * 60
        rs_pts_val = rs_raw_val * 0.25
        stg_pts    = {2: 10.0, 1: 4.0, 3: 2.0, 4: 0.0}.get(stage, 5.0)
        ad_pts     = max(-5.0, min(5.0, ad * 0.5))
        comp_score = round(min(100.0, max(0.0, base + rs_pts_val + stg_pts + ad_pts)), 1)
        grade_val  = "A" if comp_score >= 72 else "B" if comp_score >= 58 else "C" if comp_score >= 44 else "D"
        pat_pts    = 30.0
        pat_label  = "none"

    # ── Direction ─────────────────────────────────────────────────────────────
    if stage == 2 and ma_info["stack"] in ("full_bull", "partial_bull") and rsi_val >= 35:
        direction = "long"
    elif stage == 4 or ma_info["stack"] == "bear":
        direction = "avoid"
    else:
        direction = "neutral"

    # ── Multi-timeframe alignment ─────────────────────────────────────────────
    df_weekly  = _resample_weekly(df)
    df_monthly = _resample_monthly(df)
    daily_tf   = _tf_signals(df,         "Daily")
    weekly_tf  = _tf_signals(df_weekly,  "Weekly")
    monthly_tf = _tf_signals(df_monthly, "Monthly")
    mtf        = _mtf_alignment(daily_tf, weekly_tf, monthly_tf)

    # ── Score breakdown ───────────────────────────────────────────────────────
    stg_pts_val = {2: 10.0, 1: 4.0, 3: 2.0, 4: 0.0}.get(stage, 5.0)
    ad_pts_val  = round(max(-5.0, min(5.0, ad * 0.5)), 1)
    score_breakdown = {
        "pattern": {"pts": pat_pts,                    "max": 60, "label": f"Pattern quality ({pat_label})"},
        "rs":      {"pts": round(rs_raw_val * 0.25, 1), "max": 25, "label": f"RS {rs_raw_val:.0f} ({rs_lbl})"},
        "stage":   {"pts": stg_pts_val,                "max": 10, "label": f"Weinstein {['?','S1','S2','S3','S4'][stage] if 1<=stage<=4 else '?'}"},
        "ad":      {"pts": ad_pts_val,                 "max":  5, "label": f"A/D Net ({ad:+d})"},
        "total":   comp_score,
    }

    # ── Serialise setups ──────────────────────────────────────────────────────
    def _sd(s) -> dict:
        return {
            "setup_type":      s.setup_type,
            "state":           s.state,
            "entry":           s.entry,
            "stop":            s.stop,
            "t1":              s.t1,
            "t2":              s.t2,
            "rr":              s.rr,
            "risk_pct":        round((s.entry - s.stop) / s.entry * 100, 1) if s.entry > 0 else 0,
            "confidence":      s.confidence,
            "composite_score": s.composite_score,
            "grade":           s.grade,
            "notes":           s.notes,
        }

    return {
        # Identity
        "symbol":        symbol,
        "price":         round(price, 2),
        "pct_change":    pct_change,
        "rvol":          rvol_val,
        "vol_ratio_50d": vol_ratio,
        # Scoring
        "composite_score": comp_score,
        "grade":           grade_val,
        "direction":       direction,
        "rs_score":        rs_raw_val,
        "rs_label":        rs_lbl,
        "weinstein_stage": stage,
        # Technical
        "rsi":            round(rsi_val, 1),
        "adx":            adx_val,
        "macd_histogram": round(macd_hist, 4),
        "macd_direction": macd_direction,
        "macd_expanding": macd_expanding,
        # MA stack
        "ma_stack": ma_info,
        # Institutional
        "ad_net":    ad,
        "isc_score": isc,
        # Penalty
        "overextension_penalty": round(penalty, 3),
        # Setups
        "best_setup":    _sd(best) if best else None,
        "active_setups": [_sd(s) for s in active_setups],
        # Derived
        "checklist":          checklist_items,
        "warnings":           warning_items,
        "score_breakdown":    score_breakdown,
        # Multi-timeframe alignment
        "timeframe_alignment": mtf,
    }
