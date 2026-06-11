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
    "VCP":         2.8,   # Minervini volatility contraction pattern
    "TB":          2.5,   # wyckoff_accumulation_sos
    "WYS":         3.0,   # wyckoff_accumulation_spring
    "PP":          2.0,   # volume_breakout
    "PULL":        1.5,   # bull_flag
    "FBD":         2.0,   # double_bottom
    # ── Trend indicators ──────────────────────────────────────────────────────
    "Stage":       2.5,   # Weinstein stage (structural filter, highest indicator weight)
    "TrendTmpl":   1.8,   # Minervini 8-point Trend Template (SMA50/150/200 + 52wk position + RS)
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
    "VCP":        0.72,
    "TB":         0.70,
    "WYS":        0.75,
    "PP":         0.65,
    "PULL":       0.63,
    "FBD":        0.68,
    "Stage":      0.72,
    "TrendTmpl":  0.72,   # Minervini reports high win-rates for stocks meeting the full template
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
    "EP": "trend", "VCP": "trend", "TB": "trend", "WYS": "trend",
    "PP": "trend", "PULL": "trend", "FBD": "trend",
    "Stage": "trend", "TrendTmpl": "trend", "EMA": "trend", "Supertrend": "trend",
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
# The weekly tailwind only CONFIRMS a live daily bullish signal — it must never
# manufacture one. When the daily vote has rolled over to neutral (the signature
# of a local top, where the daily deteriorates before the lagging weekly), the
# bullish weekly bonus is scaled down sharply so it can't prop up the score.
HT_UNCONFIRMED_SCALE        = 0.2   # multiplier on the weekly bonus when daily ≠ long
HT_NEUTRAL_SUPPORT_BONUS    = 1.0   # weekly neutral but in same stage

# ── Overextension penalty constants ──────────────────────────────────────────
RSI_EXHAUSTION_THRESHOLD  = 80.0
EMA21_EXTENSION_THRESHOLD = 0.08
OVEREXT_PENALTY_SCALE     = 0.5

# ── Local-top / distribution penalty constants ───────────────────────────────
# These catch topping signatures that the still-long daily + lagging weekly can
# miss: institutional selling and momentum failing right at the highs.
DIST_DAYS_WINDOW        = 10    # look-back for the distribution-day cluster
DIST_DAYS_THRESHOLD     = 3     # ≥3 distribution days in the window = cluster
DIST_CLUSTER_PENALTY    = 3.0
MACD_FADE_PENALTY       = 2.0   # MACD histogram rolling over from positive
RSI_DIVERGENCE_PENALTY  = 3.0   # price higher high, RSI lower high
DISTRIBUTION_PENALTY_CAP = 8.0  # max total from this penalty

P_GRADE_THRESHOLDS = {"A": 75, "B": 60, "C": 45}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _regime_from_stage(stage: int) -> str:
    if stage == 2: return "trend"
    if stage == 4: return "range"
    return "transition"


def _mult(source: str, regime: str) -> float:
    sig_cls = SIGNAL_CLASS.get(source, "trend")
    return REGIME_MULT.get(regime, {}).get(sig_cls, 1.0)


def _rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs    = gain / loss.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def _rsi(close: pd.Series, period: int = 14) -> float:
    val = _rsi_series(close, period).iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def _distribution_penalty(df: pd.DataFrame, direction_out: str) -> tuple[float, list[str]]:
    """Local-top / distribution penalty (post-vote).

    Catches topping signatures that a still-long daily + lagging weekly miss:
      1. Distribution-day cluster — ≥3 down days on rising volume in 10 bars
         (O'Neill institutional-selling tell)
      2. MACD histogram rolling over from positive — momentum fading at highs
      3. Bearish RSI divergence — price prints a higher high while RSI prints a
         lower high

    Only applied to long / neutral (bullish-leaning) names — a short-biased name
    is already scored down. Returns (penalty_pts, notes), capped at the cap.
    """
    if direction_out == "short" or len(df) < 30:
        return 0.0, []

    close = df["close"]
    vol   = df["volume"]
    penalty = 0.0
    notes: list[str] = []

    # 1) Distribution-day cluster
    dist = 0
    for i in range(max(1, len(df) - DIST_DAYS_WINDOW), len(df)):
        c, pc = float(close.iloc[i]), float(close.iloc[i - 1])
        v, pv = float(vol.iloc[i]),   float(vol.iloc[i - 1])
        if pc > 0 and (c - pc) / pc <= -0.002 and v > pv:
            dist += 1
    if dist >= DIST_DAYS_THRESHOLD:
        penalty += DIST_CLUSTER_PENALTY
        notes.append(f"{dist} distribution days in last {DIST_DAYS_WINDOW} — institutional selling −{DIST_CLUSTER_PENALTY:.1f}pts")

    # 2) MACD histogram fading from positive (3-bar decline while > 0)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    hist  = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    if len(hist) >= 4:
        h = [float(hist.iloc[-i]) for i in range(1, 5)]  # h[0] = latest
        if h[0] > 0 and h[0] < h[1] < h[2]:
            penalty += MACD_FADE_PENALTY
            notes.append(f"MACD histogram fading at highs −{MACD_FADE_PENALTY:.1f}pts")

    # 3) Bearish RSI divergence — recent higher high in price, lower high in RSI
    rsi_s = _rsi_series(close, 14)
    look  = 20
    if len(close) > look + 5:
        recent = close.iloc[-5:]                 # the most recent swing
        prior  = close.iloc[-(look + 5):-5]      # the prior swing window
        if not prior.empty:
            recent_hi_idx = recent.idxmax()
            prior_hi_idx  = prior.idxmax()
            if float(recent.max()) >= float(prior.max()):       # price = higher/equal high
                rsi_recent = float(rsi_s.loc[recent_hi_idx])
                rsi_prior  = float(rsi_s.loc[prior_hi_idx])
                if not (pd.isna(rsi_recent) or pd.isna(rsi_prior)) and rsi_recent < rsi_prior - 2:
                    penalty += RSI_DIVERGENCE_PENALTY
                    notes.append(f"bearish RSI divergence (RSI {rsi_recent:.0f} < {rsi_prior:.0f} at a higher price) −{RSI_DIVERGENCE_PENALTY:.1f}pts")

    return min(penalty, DISTRIBUTION_PENALTY_CAP), notes


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


def _trend_template(
    df: pd.DataFrame,
    rs_score: float | None,
) -> tuple[str | None, float, int, int, list[dict]]:
    """Mark Minervini's 8-point Trend Template (from "Trade Like a Stock Market Wizard").

    A structural leadership filter. The eight criteria:
      1. Price above both the 150-day AND 200-day SMA
      2. 150-day SMA above the 200-day SMA
      3. 200-day SMA trending up (rising vs ~1 month ago)
      4. 50-day SMA above both the 150-day and 200-day SMA
      5. Price above the 50-day SMA
      6. Price at least 30% above its 52-week low
      7. Price within 25% of its 52-week high
      8. RS rank >= 70  (only evaluated when rs_score is provided)

    Returns (direction, strength, passed, total, criteria).
      direction = "bullish" when >=50% of criteria pass, else "bearish".
      strength  = pass fraction (bullish) or fail fraction (bearish), in 0-1.
      criteria  = list of {label, met, detail} dicts, one per criterion.
      Returns (None, 0, 0, 0, []) when there is insufficient history (<200 bars).
    """
    close = df["close"]
    if len(close) < 200:
        return None, 0.0, 0, 0, []

    price       = float(close.iloc[-1])
    sma50       = float(close.rolling(50).mean().iloc[-1])
    sma150      = float(close.rolling(150).mean().iloc[-1])
    sma200_s    = close.rolling(200).mean()
    sma200      = float(sma200_s.iloc[-1])
    sma200_prev = float(sma200_s.iloc[-21]) if len(sma200_s) >= 21 else sma200  # ~1 month ago

    if any(pd.isna(x) for x in (sma50, sma150, sma200, sma200_prev)):
        return None, 0.0, 0, 0, []

    lookback = min(len(close), 252)               # ~52 trading weeks
    window   = close.iloc[-lookback:]
    hi_52    = float(window.max())
    lo_52    = float(window.min())

    pct_above_low  = (price / lo_52 - 1.0) * 100 if lo_52 > 0 else 0.0
    pct_below_high = (1.0 - price / hi_52) * 100 if hi_52 > 0 else 100.0

    # (label, met, detail) — detail shows the live values behind each check
    criteria: list[dict] = [
        {"label": "Price above 150 & 200-day SMA", "met": price > sma150 and price > sma200,
         "detail": f"${price:.2f} vs SMA150 ${sma150:.2f} / SMA200 ${sma200:.2f}"},
        {"label": "150-day SMA above 200-day SMA", "met": sma150 > sma200,
         "detail": f"SMA150 ${sma150:.2f} vs SMA200 ${sma200:.2f}"},
        {"label": "200-day SMA trending up", "met": sma200 > sma200_prev,
         "detail": f"now ${sma200:.2f} vs ~1mo ago ${sma200_prev:.2f}"},
        {"label": "50-day SMA above 150 & 200-day SMA", "met": sma50 > sma150 and sma50 > sma200,
         "detail": f"SMA50 ${sma50:.2f} vs SMA150 ${sma150:.2f} / SMA200 ${sma200:.2f}"},
        {"label": "Price above 50-day SMA", "met": price > sma50,
         "detail": f"${price:.2f} vs SMA50 ${sma50:.2f}"},
        {"label": "≥30% above 52-week low", "met": lo_52 > 0 and price >= lo_52 * 1.30,
         "detail": f"{pct_above_low:.0f}% above low ${lo_52:.2f}"},
        {"label": "Within 25% of 52-week high", "met": hi_52 > 0 and price >= hi_52 * 0.75,
         "detail": f"{pct_below_high:.0f}% below high ${hi_52:.2f}"},
    ]
    if rs_score is not None:
        criteria.append(
            {"label": "RS rank ≥ 70", "met": rs_score >= 70,
             "detail": f"RS {rs_score:.0f}"}
        )

    total  = len(criteria)
    passed = sum(1 for c in criteria if c["met"])
    frac   = passed / total if total else 0.0

    if frac >= 0.5:
        return "bullish", frac, passed, total, criteria
    return "bearish", (1.0 - frac), passed, total, criteria


def _ht_adjustment(
    weekly_dir: str,
    stage: int,
    direction_out: str,
) -> tuple[float, str | None]:
    """Higher-timeframe (weekly) score adjustment — post-vote bonus/penalty.

    The weekly tailwind only *confirms* a live daily bullish signal; it must
    never *manufacture* one. When the daily vote has rolled over to neutral
    (the signature of a local top, where the daily deteriorates before the
    lagging weekly), the bullish bonus is scaled by HT_UNCONFIRMED_SCALE so it
    cannot prop up the score. The bearish-weekly *penalty* is never scaled — a
    weekly headwind is a real risk regardless of the daily.
    """
    if direction_out == "short":
        # For short setups, opposing logic would mirror; skip for now
        return 0.0, None

    if weekly_dir == "bullish":
        # Scale the tailwind down unless the daily itself is confirming (long).
        scale = 1.0 if direction_out == "long" else HT_UNCONFIRMED_SCALE
        adj  = HT_ALIGNED_DIRECTION_BONUS
        if stage == 2:
            adj += HT_SUPPORTIVE_STAGE_BONUS
        adj += HT_STRONG_TREND_BONUS   # weekly bullish ⇒ strong-trend proxy
        adj *= scale
        if scale < 1.0:
            note = f"+{adj:.1f} weekly bullish ×{scale:.1f} (daily not confirming)"
        elif stage == 2:
            note = f"+{adj:.1f} weekly bullish + S2 + strong-trend confirm"
        else:
            note = f"+{adj:.1f} weekly bullish + strong-trend confirm"
        return round(adj, 2), note

    if weekly_dir == "bearish":
        # Headwind always counts at full strength (makes the score more conservative).
        adj  = -HT_OPPOSING_DIRECTION_PENALTY
        note = f"−{HT_OPPOSING_DIRECTION_PENALTY:.1f} weekly direction opposes"
        return adj, note

    # neutral weekly — only a token bonus, and only when the daily is confirming
    if stage == 2 and direction_out == "long":
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
    rs_score: float | None = None,  # RS rank 0-100 (for Minervini Trend Template criterion 8)
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
    signal_details: dict[str, str] = {}   # optional per-signal human-readable note

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

    # Trend Template — Minervini 8-point structural leadership filter
    tt_dir, tt_str, tt_passed, tt_total, _tt_criteria = _trend_template(df, rs_score)
    if tt_dir:
        raw_signals.append(("TrendTmpl", tt_dir, tt_str))
        signal_details["TrendTmpl"] = f"{tt_passed}/{tt_total} criteria met"

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

        comp = {
            "source":       source,
            "direction":    direction,
            "strength":     round(strength, 3),
            "weight":       round(w, 2),
            "accuracy":     acc,
            "regime_mult":  round(mult, 2),
            "contribution": round(contribution, 3),
        }
        if source in signal_details:
            comp["detail"] = signal_details[source]
        components.append(comp)

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

    # Local-top / distribution penalty — institutional selling + momentum failing at highs
    dist_pen, dist_notes = _distribution_penalty(df, direction_out)
    if dist_pen > 0:
        penalty += dist_pen
        penalty_notes.extend(dist_notes)

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
