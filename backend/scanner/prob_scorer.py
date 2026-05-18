"""Probability scorer — ported from github.com/sav2125/technical-analysis.

The P Score aggregates heterogeneous signals using a weighted-voting model
where each signal's contribution is scaled by three independent factors:

    contribution = strength × weight × accuracy_factor × regime_multiplier

Long contributions are summed and normalised vs their maximum possible
sum, then a 1.2× agreement bonus is applied when ≥ 70% of weighted
signals align.  A separate higher-timeframe adjustment is added after
the vote (weekly bullish + S2 → up to +7.5 pts; weekly bearish → −6 pts).
Overextension penalties (RSI > 80, price far above EMA21) are applied last.

Signal set matches scripts/scoring/probability.py + indicators/*.py
from github.com/sav2125/technical-analysis.

Weights:          config.yaml → scoring.weights
Regime mults:     config.yaml → regime.weight_multipliers
HT adjustment:    config.yaml → scoring.higher_timeframe_confirmation
"""
from __future__ import annotations

import pandas as pd
import numpy as np

# ── Signal weights  (from config.yaml → scoring.weights) ─────────────────────
WEIGHTS: dict[str, float] = {
    # ── Setup patterns ────────────────────────────────────────────────────────
    "EP":          3.0,   # stage2_breakout
    "TB":          2.5,   # wyckoff_accumulation_sos
    "WYS":         3.0,   # wyckoff_accumulation_spring
    "PP":          2.0,   # volume_breakout
    "PULL":        1.5,   # bull_flag
    "FBD":         2.0,   # double_bottom
    # ── Trend indicators ──────────────────────────────────────────────────────
    "Stage":       2.5,   # Weinstein stage (structural filter, highest indicator weight)
    "EMA":         1.5,   # EMA alignment stack (price > EMA21 > EMA50)
    "Supertrend":  1.0,   # ATR trailing trend line (period=10, mult=3.0)
    "OBV":         1.5,   # On-Balance Volume trend (config: volume indicators)
    "CMF":         1.2,   # Chaikin Money Flow (config: volume indicators)
    "MACD":        1.0,   # MACD histogram direction
    # ── Mean-reversion / momentum ──────────────────────────────────────────────
    "RSI":         1.0,   # RSI 14 — oscillator signal
    "Stochastic":  0.8,   # %K oscillator — overbought / oversold
    "BB":          0.85,  # Bollinger Bands %B — near lower = bullish, near upper = bearish
    "KC":          0.85,  # Keltner Channels — price outside channel
    # ── Institutional flow (already partially in EMA/ICS but standalone here) ─
    "ICS":         1.2,   # Institutional Composite Score (OBV+CMF+A/D+MFI → 0-100)
    "ADNet":       1.0,   # O'Neill A/D net days (accumulation / distribution count)
}

# ── Accuracy factors (backtested win-rates from signal_weights.yaml) ──────────
ACCURACY: dict[str, float] = {
    "EP":         0.72,
    "TB":         0.70,
    "WYS":        0.75,
    "PP":         0.65,
    "PULL":       0.63,
    "FBD":        0.68,
    "Stage":      0.72,
    "EMA":        0.70,
    "Supertrend": 0.71,
    "OBV":        0.68,
    "CMF":        0.68,
    "MACD":       0.65,
    "RSI":        0.62,
    "Stochastic": 0.62,
    "BB":         0.68,
    "KC":         0.68,
    "ICS":        0.68,
    "ADNet":      0.65,
}

# ── Signal classification: "trend" vs "mean_reversion" ───────────────────────
# Source: scripts/scoring/regime.py — TREND_SOURCES / MEAN_REVERSION_SOURCES.
SIGNAL_CLASS: dict[str, str] = {
    # Trend-following
    "EP": "trend", "TB": "trend", "WYS": "trend",
    "PP": "trend", "PULL": "trend", "FBD": "trend",
    "Stage": "trend", "EMA": "trend", "Supertrend": "trend",
    "OBV": "trend", "CMF": "trend", "MACD": "trend",
    "ICS": "trend", "ADNet": "trend", "KC": "trend",
    # Mean-reversion oscillators
    "RSI": "mean_reversion",
    "Stochastic": "mean_reversion",
    "BB": "mean_reversion",
}

# ── Regime multipliers (config.yaml → regime.weight_multipliers) ──────────────
REGIME_MULT: dict[str, dict[str, float]] = {
    "trend":      {"trend": 1.15, "mean_reversion": 0.70},
    "range":      {"trend": 0.75, "mean_reversion": 1.15},
    "transition": {"trend": 0.95, "mean_reversion": 0.85},
}

AGREEMENT_BONUS     = 1.2
AGREEMENT_THRESHOLD = 0.70

# ── Higher-timeframe adjustment (config.yaml → scoring.higher_timeframe_confirmation)
# Applied as a flat pts bonus/penalty AFTER the base vote score is computed.
# Mirrors the reference implementation exactly.
HT_ALIGNED_DIRECTION_BONUS  = 4.0   # weekly direction aligns with daily
HT_SUPPORTIVE_STAGE_BONUS   = 2.0   # weekly also in S2 advance
HT_STRONG_TREND_BONUS       = 1.5   # weekly trend score > 55 (we approximate via weekly_dir==bullish)
HT_OPPOSING_DIRECTION_PENALTY = 6.0  # weekly opposes the daily signal
HT_NEUTRAL_SUPPORT_BONUS    = 1.0   # weekly neutral but in same stage

# ── Overextension penalty constants ──────────────────────────────────────────
RSI_EXHAUSTION_THRESHOLD  = 80.0
EMA21_EXTENSION_THRESHOLD = 0.08
OVEREXT_PENALTY_SCALE     = 0.5

P_GRADE_THRESHOLDS = {"A": 75, "B": 60, "C": 45}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _regime_from_stage(stage: int) -> str:
    if stage == 2: return "trend"
    if stage == 4: return "range"
    return "transition"


def _mult(source: str, regime: str) -> float:
    sig_cls = SIGNAL_CLASS.get(source, "trend")
    return REGIME_MULT.get(regime, {}).get(sig_cls, 1.0)


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs    = gain / loss.replace(0, float("nan"))
    series = 100 - 100 / (1 + rs)
    val = series.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def _macd_hist(close: pd.Series) -> tuple[float, float]:
    """Returns (latest histogram, prev histogram)."""
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    line   = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    hist   = line - signal
    h1 = float(hist.iloc[-1])  if not pd.isna(hist.iloc[-1])  else 0.0
    h0 = float(hist.iloc[-2])  if len(hist) >= 2 and not pd.isna(hist.iloc[-2]) else h1
    return h1, h0


def _supertrend(df: pd.DataFrame, period: int = 10, mult: float = 3.0) -> tuple[str | None, float]:
    """ATR-based trailing trend indicator. Returns (direction, strength)."""
    if len(df) < period + 2:
        return None, 0.0
    hl2  = (df["high"] + df["low"]) / 2
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    upper = hl2 + mult * atr
    lower = hl2 - mult * atr

    st  = pd.Series(index=df.index, dtype=float)
    dir_ = pd.Series(index=df.index, dtype=float)
    st.iloc[period]  = upper.iloc[period]
    dir_.iloc[period] = -1.0

    for i in range(period + 1, len(df)):
        prev_st  = st.iloc[i - 1]
        close_i  = df["close"].iloc[i]
        close_pm = df["close"].iloc[i - 1]

        if close_pm <= prev_st:
            new_st = min(upper.iloc[i], prev_st)
            d = -1.0
            if close_i > new_st:
                d = 1.0
                new_st = lower.iloc[i]
        else:
            new_st = max(lower.iloc[i], prev_st)
            d = 1.0
            if close_i < new_st:
                d = -1.0
                new_st = upper.iloc[i]
        st.iloc[i]   = new_st
        dir_.iloc[i] = d

    last_dir = dir_.iloc[-1]
    if last_dir == 1.0:  return "bullish", 0.7
    if last_dir == -1.0: return "bearish", 0.7
    return None, 0.0


def _bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> tuple[str | None, float]:
    """Bollinger Bands — bullish near lower, bearish near upper."""
    close = df["close"]
    if len(close) < period:
        return None, 0.0
    sma    = close.rolling(period).mean()
    std    = close.rolling(period).std()
    upper  = sma + std_dev * std
    lower  = sma - std_dev * std

    price = float(close.iloc[-1])
    lo    = float(lower.iloc[-1])
    hi    = float(upper.iloc[-1])
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return None, 0.0

    pct_b = (price - lo) / (hi - lo)   # 0 = at lower, 1 = at upper
    if price <= lo:         return "bullish", 0.7
    if price >= hi:         return "bearish", 0.7
    if pct_b < 0.30:        return "bullish", 0.4
    if pct_b > 0.70:        return "bearish", 0.4
    return None, 0.0        # neutral middle band — skip


def _keltner(df: pd.DataFrame, period: int = 20, mult: float = 1.5) -> tuple[str | None, float]:
    """Keltner Channels — ATR-based dynamic channel."""
    close = df["close"]
    if len(close) < period:
        return None, 0.0
    ema    = close.ewm(span=period, adjust=False).mean()
    prev_c = close.shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_c).abs(),
        (df["low"]  - prev_c).abs(),
    ], axis=1).max(axis=1)
    atr   = tr.rolling(period).mean()
    upper = ema + mult * atr
    lower = ema - mult * atr

    price = float(close.iloc[-1])
    lo    = float(lower.iloc[-1])
    hi    = float(upper.iloc[-1])
    if pd.isna(lo) or pd.isna(hi):
        return None, 0.0

    if price <= lo:  return "bullish", 0.7
    if price >= hi:  return "bearish", 0.7
    return None, 0.0    # inside channel = neutral


def _obv_signal(df: pd.DataFrame) -> tuple[str | None, float]:
    """On-Balance Volume — rising = bullish institutional interest."""
    close  = df["close"]
    volume = df["volume"]
    if len(close) < 21:
        return None, 0.0
    obv    = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    recent = float(obv.iloc[-1])
    past   = float(obv.iloc[-21])
    denom  = abs(past) if abs(past) > 0 else 1.0
    slope  = (recent - past) / denom
    if recent > past:
        return "bullish", min(0.9, 0.4 + abs(slope) * 5)
    if recent < past:
        return "bearish", min(0.9, 0.4 + abs(slope) * 5)
    return None, 0.0


def _cmf_signal(df: pd.DataFrame, period: int = 20) -> tuple[str | None, float]:
    """Chaikin Money Flow — positive = money flowing in."""
    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]
    if len(close) < period:
        return None, 0.0
    hl_range = (high - low).replace(0, float("nan"))
    mf_mult  = ((close - low) - (high - close)) / hl_range
    mf_vol   = mf_mult * vol
    cmf_val  = float(
        mf_vol.rolling(period).sum().iloc[-1] /
        vol.rolling(period).sum().replace(0, float("nan")).iloc[-1]
    )
    if pd.isna(cmf_val):
        return None, 0.0
    if cmf_val > 0.05:   return "bullish", min(0.9, abs(cmf_val) * 4)
    if cmf_val < -0.05:  return "bearish", min(0.9, abs(cmf_val) * 4)
    return None, 0.0


def _stochastic_signal(df: pd.DataFrame, k: int = 14, d: int = 3) -> tuple[str | None, float]:
    """Stochastic %K — overbought / oversold oscillator."""
    close, high, low = df["close"], df["high"], df["low"]
    if len(close) < k:
        return None, 0.0
    lo_min  = low.rolling(k).min()
    hi_max  = high.rolling(k).max()
    denom   = (hi_max - lo_min).replace(0, float("nan"))
    pct_k   = 100 * (close - lo_min) / denom
    k_val   = float(pct_k.iloc[-1])
    if pd.isna(k_val):
        return None, 0.0
    if k_val < 20:   return "bullish", (20 - k_val) / 20.0
    if k_val > 80:   return "bearish", (k_val - 80) / 20.0
    return None, 0.0  # neutral zone


def _ht_adjustment(
    weekly_dir: str,
    stage: int,
    direction_out: str,
) -> tuple[float, str | None]:
    """Higher-timeframe (weekly) score adjustment — post-vote flat bonus/penalty.

    Mirrors config.yaml → scoring.higher_timeframe_confirmation.
    Only applied when the dominant direction is long (bullish bias).
    """
    if direction_out not in ("long", "neutral"):
        # For short setups, opposing logic would mirror; skip for now
        return 0.0, None

    if weekly_dir == "bullish":
        adj  = HT_ALIGNED_DIRECTION_BONUS
        note = f"+{HT_ALIGNED_DIRECTION_BONUS:.1f} weekly direction aligns"
        if stage == 2:
            adj  += HT_SUPPORTIVE_STAGE_BONUS
            note += f" +{HT_SUPPORTIVE_STAGE_BONUS:.1f} S2 support"
        # Approximate strong_trend_bonus: weekly bullish always qualifies
        adj  += HT_STRONG_TREND_BONUS
        note += f" +{HT_STRONG_TREND_BONUS:.1f} strong trend"
        return adj, note

    if weekly_dir == "bearish":
        adj  = -HT_OPPOSING_DIRECTION_PENALTY
        note = f"−{HT_OPPOSING_DIRECTION_PENALTY:.1f} weekly direction opposes"
        return adj, note

    # neutral weekly
    if stage == 2:
        adj  = HT_NEUTRAL_SUPPORT_BONUS
        note = f"+{HT_NEUTRAL_SUPPORT_BONUS:.1f} weekly neutral / S2 support"
        return adj, note

    return 0.0, None


# ── Public API ────────────────────────────────────────────────────────────────

def compute_prob_score(
    df: pd.DataFrame,
    stage: int,
    isc: float,
    ad_net: int,
    ma_stack: str,           # "full_bull" | "partial_bull" | "mixed" | "bear"
    active_setups: list,     # list of Setup objects
    weekly_dir: str = "neutral",  # "bullish" | "neutral" | "bearish"
) -> dict:
    """Compute the P Score for a single stock.

    Signal set matches github.com/sav2125/technical-analysis:
      Voting signals:  RSI, MACD, Supertrend, EMA, Stage, OBV, CMF,
                       Stochastic, BB (%B), KC, ICS, ADNet, setup pattern(s)
      Post-vote:       Higher-timeframe weekly adjustment (±0–7.5 pts)
      Post-vote:       Overextension penalty (RSI > 80, price > 8% above EMA21)

    Returns
    -------
    dict with keys: prob_score, prob_grade, prob_direction, prob_components,
                    prob_agreement, prob_regime, prob_penalty, prob_penalty_notes
    """
    if df is None or len(df) < 20:
        return {
            "prob_score": 0.0, "prob_grade": "D", "prob_direction": "neutral",
            "prob_components": [], "prob_agreement": 0.0, "prob_regime": "transition",
            "prob_penalty": 0.0, "prob_penalty_notes": [],
        }

    close  = df["close"]
    regime = _regime_from_stage(stage)
    price  = float(close.iloc[-1])

    # ── Pre-compute shared indicator values ───────────────────────────────────
    rsi_val          = _rsi(close)
    hist_val, hist_prev = _macd_hist(close)
    macd_expanding   = (hist_val > 0 and hist_val > hist_prev) or (hist_val < 0 and hist_val < hist_prev)

    ema21_s = close.ewm(span=21, adjust=False).mean()
    ema21   = float(ema21_s.iloc[-1])

    # ── Build raw signal list ─────────────────────────────────────────────────
    # Each entry: (source, direction, strength)
    raw_signals: list[tuple[str, str, float]] = []

    # ── Trend indicators ──────────────────────────────────────────────────────

    # Supertrend (period=10, mult=3.0) — directional trailing stop
    st_dir, st_str = _supertrend(df)
    if st_dir:
        raw_signals.append(("Supertrend", st_dir, st_str))

    # EMA alignment stack — price vs EMA21 vs EMA50
    ema_str_map = {"full_bull": 0.9, "partial_bull": 0.6, "mixed": 0.3, "bear": 0.85}
    ema_dir_map = {"full_bull": "bullish", "partial_bull": "bullish", "mixed": None, "bear": "bearish"}
    ema_dir = ema_dir_map.get(ma_stack)
    if ema_dir:
        raw_signals.append(("EMA", ema_dir, ema_str_map.get(ma_stack, 0.3)))

    # MACD — histogram direction + expanding flag
    macd_strength = 0.8 if macd_expanding else 0.5
    raw_signals.append(("MACD", "bullish" if hist_val > 0 else "bearish", macd_strength))

    # Weinstein stage — primary structural filter
    stage_cfg: dict[int, tuple[str, float]] = {
        2: ("bullish", 1.00),
        1: ("bullish", 0.40),
        3: ("bearish", 0.70),
        4: ("bearish", 1.00),
    }
    if stage in stage_cfg:
        s_dir, s_str = stage_cfg[stage]
        raw_signals.append(("Stage", s_dir, s_str))

    # OBV — on-balance volume trend
    obv_dir, obv_str = _obv_signal(df)
    if obv_dir:
        raw_signals.append(("OBV", obv_dir, obv_str))

    # CMF — Chaikin Money Flow
    cmf_dir, cmf_str = _cmf_signal(df)
    if cmf_dir:
        raw_signals.append(("CMF", cmf_dir, cmf_str))

    # ICS — Institutional Composite Score
    if abs(isc - 50) > 5:
        raw_signals.append(("ICS", "bullish" if isc > 50 else "bearish", isc / 100.0))

    # A/D Net — O'Neill accumulation day count
    if ad_net != 0:
        ad_str = min(abs(ad_net) / 10.0, 1.0)
        raw_signals.append(("ADNet", "bullish" if ad_net > 0 else "bearish", ad_str))

    # ── Mean-reversion / volatility signals ───────────────────────────────────

    # RSI — oscillator; strength = distance from neutral 50
    rsi_strength = abs(rsi_val - 50) / 50.0
    raw_signals.append(("RSI", "bullish" if rsi_val > 50 else "bearish", rsi_strength))

    # Stochastic %K — overbought / oversold
    sto_dir, sto_str = _stochastic_signal(df)
    if sto_dir:
        raw_signals.append(("Stochastic", sto_dir, sto_str))

    # Bollinger Bands %B
    bb_dir, bb_str = _bollinger(df)
    if bb_dir:
        raw_signals.append(("BB", bb_dir, bb_str))

    # Keltner Channels
    kc_dir, kc_str = _keltner(df)
    if kc_dir:
        raw_signals.append(("KC", kc_dir, kc_str))

    # ── Setup pattern signals ─────────────────────────────────────────────────
    for setup in (active_setups or []):
        raw_signals.append((setup.setup_type, "bullish", float(setup.confidence)))

    # ── Weighted voting ───────────────────────────────────────────────────────
    long_score:  float = 0.0
    long_max:    float = 0.0
    short_score: float = 0.0
    short_max:   float = 0.0
    components: list[dict] = []

    for source, direction, strength in raw_signals:
        w    = WEIGHTS.get(source, 1.0)
        acc  = ACCURACY.get(source, 0.70)
        mult = _mult(source, regime)
        eff_w        = w * mult
        contribution = strength * eff_w * acc

        components.append({
            "source":       source,
            "direction":    direction,
            "strength":     round(strength, 3),
            "weight":       round(w, 2),
            "accuracy":     acc,
            "regime_mult":  round(mult, 2),
            "contribution": round(contribution, 3),
        })

        if direction == "bullish":
            long_score += contribution
            long_max   += eff_w
        else:
            short_score += contribution
            short_max   += eff_w

    # ── Normalise + agreement bonus ───────────────────────────────────────────
    total = long_score + short_score
    if total <= 0:
        return {
            "prob_score": 0.0, "prob_grade": "D", "prob_direction": "neutral",
            "prob_components": components, "prob_agreement": 0.0, "prob_regime": regime,
            "prob_penalty": 0.0, "prob_penalty_notes": [],
        }

    if long_score >= short_score:
        dominant_side  = "bullish"
        dominant_score = long_score
        dominant_max   = long_max
    else:
        dominant_side  = "bearish"
        dominant_score = short_score
        dominant_max   = short_max

    agreement_ratio = max(long_score, short_score) / total
    agreement_mult  = AGREEMENT_BONUS if agreement_ratio >= AGREEMENT_THRESHOLD else 1.0

    raw_score = (dominant_score / dominant_max) if dominant_max > 0 else 0.0
    composite = min(100.0, raw_score * 100.0 * agreement_mult)

    if agreement_ratio < 0.60:
        direction_out = "neutral"
    elif dominant_side == "bullish":
        direction_out = "long"
    else:
        direction_out = "short"

    # ── Higher-timeframe adjustment (weekly direction) ────────────────────────
    # Applied as a flat bonus/penalty on top of the base vote score.
    # Source: config.yaml → scoring.higher_timeframe_confirmation
    ht_adj, ht_note = _ht_adjustment(weekly_dir, stage, direction_out)
    ht_components: list[dict] = []
    if ht_adj != 0 and ht_note:
        composite = max(0.0, min(100.0, composite + ht_adj))
        ht_components.append({
            "source":       "WeeklyTF",
            "direction":    "bullish" if ht_adj > 0 else "bearish",
            "strength":     abs(ht_adj) / 10.0,
            "weight":       0.0,        # adjustment, not a voting signal
            "accuracy":     1.0,
            "regime_mult":  1.0,
            "contribution": round(ht_adj, 2),
        })

    all_components = ht_components + components   # weekly adjustment first for visibility

    # ── Overextension penalty ─────────────────────────────────────────────────
    penalty = 0.0
    penalty_notes: list[str] = []

    if direction_out == "long" and rsi_val > RSI_EXHAUSTION_THRESHOLD:
        p = (rsi_val - RSI_EXHAUSTION_THRESHOLD) * OVEREXT_PENALTY_SCALE
        penalty += p
        penalty_notes.append(f"RSI {rsi_val:.0f} exhaustion −{p:.1f}pts")

    if ema21 > 0 and price > ema21:
        ext = (price - ema21) / ema21
        if ext > EMA21_EXTENSION_THRESHOLD:
            p = min(10.0, (ext - EMA21_EXTENSION_THRESHOLD) * 100 * OVEREXT_PENALTY_SCALE)
            penalty += p
            penalty_notes.append(f"+{ext*100:.0f}% above EMA21 −{p:.1f}pts")

    composite = max(0.0, composite - penalty)

    # ── Grade ─────────────────────────────────────────────────────────────────
    if composite >= P_GRADE_THRESHOLDS["A"]:   grade = "A"
    elif composite >= P_GRADE_THRESHOLDS["B"]: grade = "B"
    elif composite >= P_GRADE_THRESHOLDS["C"]: grade = "C"
    else:                                       grade = "D"

    return {
        "prob_score":         round(composite, 1),
        "prob_grade":         grade,
        "prob_direction":     direction_out,
        "prob_components":    all_components,
        "prob_agreement":     round(agreement_ratio, 3),
        "prob_regime":        regime,
        "prob_penalty":       round(penalty, 1),
        "prob_penalty_notes": penalty_notes,
    }
