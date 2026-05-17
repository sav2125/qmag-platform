"""Probability scorer — ported from github.com/sav2125/technical-analysis.

The P Score aggregates heterogeneous signals using a weighted-voting model
where each signal's contribution is scaled by three independent factors:

    contribution = strength × weight × accuracy_factor × regime_multiplier

Long contributions are summed and normalised vs their maximum possible
sum, then a 1.2× agreement bonus is applied when ≥ 70% of weighted
signals align.  Overextension penalties (RSI > 80, price far above EMA21)
are applied after the raw composite is computed.

Source: scripts/scoring/probability.py  (github.com/sav2125/technical-analysis)
Weights: config.yaml → scoring.weights
Regime multipliers: config.yaml → regime.weight_multipliers
"""
from __future__ import annotations

import math
import pandas as pd

# ── Signal weights  (from config.yaml → scoring.weights) ─────────────────────
# Pattern weights map to the nearest equivalent in the source config.
#   EP   ≈ stage2_breakout           (3.0)
#   TB   ≈ wyckoff_accumulation_sos  (2.5)
#   WYS  = wyckoff_accumulation_spring (3.0)
#   PP   ≈ volume_breakout           (2.0)
#   PULL ≈ bull_flag                 (1.5)
#   FBD  ≈ double_bottom             (2.0)
# Indicator weights use source values directly (RSI=1.0, MACD=1.0, OBV≈EMA=1.5, CMF≈ICS=1.2).
WEIGHTS: dict[str, float] = {
    # Patterns
    "EP":    3.0,
    "TB":    2.5,
    "WYS":   3.0,
    "PP":    2.0,
    "PULL":  1.5,
    "FBD":   2.0,
    # Indicators
    "RSI":   1.0,
    "MACD":  1.0,
    "EMA":   1.5,   # EMA alignment stack (OBV equivalent)
    "Stage": 2.5,   # Weinstein stage — most important structural filter
    "ICS":   1.2,   # Institutional Composite Score (CMF equivalent)
    "ADNet": 1.0,   # O'Neill A/D net days
}

# ── Accuracy factors (historical win-rates; update via backtest) ──────────────
# Source defaults to 0.70 for all signals without backtest data.
# These are reasonable priors for Qullamaggie-style setups.
ACCURACY: dict[str, float] = {
    "EP":    0.72,
    "TB":    0.70,
    "WYS":   0.75,
    "PP":    0.65,
    "PULL":  0.63,
    "FBD":   0.68,
    "RSI":   0.62,
    "MACD":  0.65,
    "EMA":   0.70,
    "Stage": 0.72,
    "ICS":   0.68,
    "ADNet": 0.65,
}

# ── Signal classification: "trend" vs "mean_reversion" ───────────────────────
# Source: scripts/scoring/regime.py — TREND_SOURCES / MEAN_REVERSION_SOURCES.
# RSI is a mean-reversion oscillator; everything else is trend-following.
SIGNAL_CLASS: dict[str, str] = {
    "EP": "trend", "TB": "trend", "WYS": "trend",
    "PP": "trend", "PULL": "trend", "FBD": "trend",
    "MACD": "trend", "EMA": "trend", "Stage": "trend",
    "ICS": "trend", "ADNet": "trend",
    "RSI": "mean_reversion",
}

# ── Regime multipliers (from config.yaml → regime.weight_multipliers) ─────────
REGIME_MULT: dict[str, dict[str, float]] = {
    "trend":      {"trend": 1.15, "mean_reversion": 0.70},
    "range":      {"trend": 0.75, "mean_reversion": 1.15},
    "transition": {"trend": 0.95, "mean_reversion": 0.85},
}

# Directional agreement bonus + threshold (from config.yaml)
AGREEMENT_BONUS     = 1.2
AGREEMENT_THRESHOLD = 0.70

# Overextension penalty constants (from probability.apply_overextension_penalty)
RSI_EXHAUSTION_THRESHOLD      = 80.0   # longs above this are penalised
EMA21_EXTENSION_THRESHOLD     = 0.08   # 8% above EMA21 starts penalty
OVEREXT_PENALTY_SCALE         = 0.5    # points per RSI unit / pct unit

# P-Score grade thresholds (from probability.compute_grade in source)
P_GRADE_THRESHOLDS = {"A": 75, "B": 60, "C": 45}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _regime_from_stage(stage: int) -> str:
    """Map Weinstein stage to the three-state regime used by the scorer."""
    if stage == 2:   return "trend"        # advancing — strong uptrend
    if stage == 4:   return "range"        # declining — downtrend / distribution
    return "transition"                    # basing or topping


def _mult(source: str, regime: str) -> float:
    sig_cls = SIGNAL_CLASS.get(source, "trend")
    return REGIME_MULT.get(regime, {}).get(sig_cls, 1.0)


def _rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs    = gain / loss.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def _macd_hist(close: pd.Series) -> pd.Series:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    line  = ema12 - ema26
    signal= line.ewm(span=9, adjust=False).mean()
    return line - signal


# ── Public API ────────────────────────────────────────────────────────────────

def compute_prob_score(
    df: pd.DataFrame,
    stage: int,
    isc: float,
    ad_net: int,
    ma_stack: str,              # "full_bull" | "partial_bull" | "mixed" | "bear"
    active_setups: list,        # list of Setup objects (patterns that fired)
) -> dict:
    """Compute the P Score for a single stock.

    Returns
    -------
    dict with keys:
        prob_score   : float 0–100
        prob_grade   : str   "A" | "B" | "C" | "D"
        prob_direction: str  "long" | "neutral" | "short"
        prob_components: list[dict]  per-signal breakdown
    """
    if df is None or len(df) < 20:
        return {"prob_score": 0.0, "prob_grade": "D", "prob_direction": "neutral", "prob_components": []}

    close  = df["close"]
    regime = _regime_from_stage(stage)
    price  = float(close.iloc[-1])

    # ── Compute raw indicator values ──────────────────────────────────────────
    rsi_s   = _rsi_series(close, 14)
    rsi_val = float(rsi_s.iloc[-1]) if not rsi_s.empty and not pd.isna(rsi_s.iloc[-1]) else 50.0

    hist_s    = _macd_hist(close)
    hist_val  = float(hist_s.iloc[-1]) if not hist_s.empty and not pd.isna(hist_s.iloc[-1]) else 0.0
    hist_prev = float(hist_s.iloc[-2]) if len(hist_s) >= 2 and not pd.isna(hist_s.iloc[-2]) else hist_val
    macd_expanding = (hist_val > 0 and hist_val > hist_prev) or (hist_val < 0 and hist_val < hist_prev)

    ema21_s = close.ewm(span=21, adjust=False).mean()
    ema21   = float(ema21_s.iloc[-1])

    # ── Build indicator signals ───────────────────────────────────────────────
    # Each signal: (source, direction, strength)
    raw_signals: list[tuple[str, str, float]] = []

    # RSI — mean-reversion oscillator; strength = distance from neutral 50
    rsi_strength = abs(rsi_val - 50) / 50.0   # 0 → flat, 1 → extreme
    raw_signals.append(("RSI", "bullish" if rsi_val > 50 else "bearish", rsi_strength))

    # MACD — trend direction + momentum; expanding histogram = stronger conviction
    macd_strength = 0.8 if macd_expanding else 0.5
    raw_signals.append(("MACD", "bullish" if hist_val > 0 else "bearish", macd_strength))

    # EMA alignment stack
    ema_str_map = {"full_bull": 0.9, "partial_bull": 0.6, "mixed": 0.3, "bear": 0.85}
    ema_dir_map = {"full_bull": "bullish", "partial_bull": "bullish", "mixed": None, "bear": "bearish"}
    ema_str = ema_str_map.get(ma_stack, 0.3)
    ema_dir = ema_dir_map.get(ma_stack)
    if ema_dir:  # skip "mixed" — no directional edge
        raw_signals.append(("EMA", ema_dir, ema_str))

    # Weinstein stage
    stage_cfg: dict[int, tuple[str, float]] = {
        2: ("bullish", 1.00),   # advancing — full conviction
        1: ("bullish", 0.40),   # basing — weak bullish lean
        3: ("bearish", 0.70),   # topping — bearish lean
        4: ("bearish", 1.00),   # declining — full conviction
    }
    if stage in stage_cfg:
        s_dir, s_str = stage_cfg[stage]
        raw_signals.append(("Stage", s_dir, s_str))

    # ICS (Institutional Composite Score)
    if abs(isc - 50) > 5:   # only count when there's a clear bias
        raw_signals.append(("ICS", "bullish" if isc > 50 else "bearish", isc / 100.0))

    # A/D net — O'Neill accumulation days
    if ad_net != 0:
        ad_str = min(abs(ad_net) / 10.0, 1.0)   # 10 net days = full strength
        raw_signals.append(("ADNet", "bullish" if ad_net > 0 else "bearish", ad_str))

    # ── Pattern signals (from fired detectors) ────────────────────────────────
    for setup in (active_setups or []):
        src = setup.setup_type   # "EP" | "TB" | etc.
        raw_signals.append((src, "bullish", float(setup.confidence)))

    # ── Weighted scoring ──────────────────────────────────────────────────────
    long_score: float  = 0.0
    long_max:   float  = 0.0
    short_score: float = 0.0
    short_max:  float  = 0.0
    components: list[dict] = []

    for source, direction, strength in raw_signals:
        w    = WEIGHTS.get(source, 1.0)
        acc  = ACCURACY.get(source, 0.70)
        mult = _mult(source, regime)
        eff_w       = w * mult           # effective weight after regime scaling
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
            long_score  += contribution
            long_max    += eff_w
        else:
            short_score += contribution
            short_max   += eff_w

    # ── Normalise and apply agreement bonus ───────────────────────────────────
    total = long_score + short_score
    if total <= 0:
        return {"prob_score": 0.0, "prob_grade": "D", "prob_direction": "neutral", "prob_components": components}

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

    # ── Overextension penalty (from apply_overextension_penalty) ─────────────
    penalty = 0.0
    penalty_notes: list[str] = []

    if direction_out == "long" and rsi_val > RSI_EXHAUSTION_THRESHOLD:
        p = (rsi_val - RSI_EXHAUSTION_THRESHOLD) * OVEREXT_PENALTY_SCALE
        penalty += p
        penalty_notes.append(f"RSI {rsi_val:.0f} exhaustion −{p:.1f}pts")

    if ema21 > 0 and price > ema21:
        extension = (price - ema21) / ema21
        if extension > EMA21_EXTENSION_THRESHOLD:
            p = min(10.0, (extension - EMA21_EXTENSION_THRESHOLD) * 100 * OVEREXT_PENALTY_SCALE)
            penalty += p
            penalty_notes.append(f"+{extension*100:.0f}% above EMA21 −{p:.1f}pts")

    composite = max(0.0, composite - penalty)

    # ── Grade ─────────────────────────────────────────────────────────────────
    if composite >= P_GRADE_THRESHOLDS["A"]:  grade = "A"
    elif composite >= P_GRADE_THRESHOLDS["B"]: grade = "B"
    elif composite >= P_GRADE_THRESHOLDS["C"]: grade = "C"
    else:                                       grade = "D"

    return {
        "prob_score":      round(composite, 1),
        "prob_grade":      grade,
        "prob_direction":  direction_out,
        "prob_components": components,
        "prob_agreement":  round(agreement_ratio, 3),
        "prob_regime":     regime,
        "prob_penalty":    round(penalty, 1),
        "prob_penalty_notes": penalty_notes,
    }
