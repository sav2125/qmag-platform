"""Qullamaggie pattern detectors: EP, Pocket Pivot, Tight Base, EMA Pullback, Failed Breakdown."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Setup:
    symbol: str
    setup_type: str          # "EP" | "TB" | "PP" | "PULL" | "FBD"
    state: str               # "base" | "breakout" | "active"
    entry: float
    stop: float
    t1: float
    t2: float
    rr: float
    confidence: float        # 0-1, raw pattern confidence
    rs_score: float          # 0-100 vs SPY
    rs_label: str
    price: float
    pct_change: float        # session %
    notes: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    weinstein_stage: int = 0   # 1-4; 0 = insufficient data
    ad_net: int = 0            # O'Neill A/D net over last 25 bars (+ = accumulation)

    @property
    def quality_score(self) -> float:
        """Quality-adjusted score: penalises wide stops, rewards good R:R.

        stop_factor: 15% stop → 0.0, 0% stop → 1.0 (clamped 0.40–1.00)
        rr_factor:   2.0 R:R → 1.0x, 4.0 R:R → 1.2x, 1.0 R:R → 0.5x
        """
        if self.entry <= 0:
            return self.confidence
        stop_pct = abs(self.entry - self.stop) / self.entry
        stop_factor = max(0.40, min(1.00, 1.0 - stop_pct / 0.15))
        rr_factor = max(0.50, min(1.20, self.rr / 2.0))
        return min(1.0, self.confidence * stop_factor * rr_factor)

    @property
    def grade(self) -> str:
        score = self.quality_score * 100
        if score >= 75:
            return "A"
        if score >= 60:
            return "B"
        if score >= 45:
            return "C"
        return "D"


# ── helpers ───────────────────────────────────────────────────────────────────

def _avg_vol(volume: pd.Series, end: int, window: int = 50) -> float:
    seg = volume.iloc[max(0, end - window): end]
    v = float(seg.mean()) if not seg.empty else float("nan")
    return v if v > 0 else float("nan")


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rr(entry: float, stop: float, target: float) -> float:
    risk = entry - stop
    if risk <= 0:
        return 0.0
    return round((target - entry) / risk, 2)


# ── Episodic Pivot ─────────────────────────────────────────────────────────────

def detect_ep(df: pd.DataFrame) -> Setup | None:
    if len(df) < 60:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    last = len(df) - 1

    for ep_idx in range(max(1, last - 60), last):
        avg = _avg_vol(volume, ep_idx)
        if np.isnan(avg):
            continue

        prior_close = float(close.iloc[ep_idx - 1])
        ep_close = float(close.iloc[ep_idx])
        ep_high = float(high.iloc[ep_idx])
        ep_low = float(low.iloc[ep_idx])
        ep_vol = float(volume.iloc[ep_idx])

        if prior_close <= 0:
            continue

        move_pct = (ep_close - prior_close) / prior_close
        vol_ratio = ep_vol / avg

        if move_pct < 0.05 or vol_ratio < 2.0:
            continue

        # Not already in a raging uptrend pre-EP
        pre_ret = (prior_close / float(close.iloc[max(0, ep_idx - 50)]) - 1)
        if pre_ret > 0.40:
            continue

        base_bars = last - ep_idx
        if base_bars < 3 or base_bars > 50:
            continue

        post_close = close.iloc[ep_idx + 1: last + 1]
        if post_close.empty:
            continue

        min_post = float(post_close.min())
        if (ep_close - min_post) / ep_close > 0.12:
            continue  # Failed to hold base

        consol_high = max(float(high.iloc[ep_idx + 1: last + 1].max()), ep_high)
        curr_close = float(close.iloc[last])
        curr_avg = _avg_vol(volume, last)
        curr_vol = float(volume.iloc[last])

        in_breakout = (
            curr_close > consol_high
            and not np.isnan(curr_avg)
            and curr_vol / curr_avg >= 1.3
        )
        state = "breakout" if in_breakout else "base"

        vol_score = min(1.0, (vol_ratio - 2.0) / 3.0)
        move_score = min(1.0, (move_pct - 0.05) / 0.15)
        tightness = float(post_close.std()) / ep_close if len(post_close) > 1 else 0.05
        tight_score = max(0.0, 1.0 - tightness / 0.04)
        conf = min(0.92, 0.55 + 0.20 * vol_score + 0.15 * move_score + 0.10 * tight_score
                   + (0.12 if in_breakout else 0))

        ep_mag = ep_close - prior_close
        t1 = round(ep_close + ep_mag, 2)
        t2 = round(ep_close + ep_mag * 2, 2)
        entry = max(curr_close, consol_high * 1.001) if in_breakout else curr_close
        stop = max(ep_low * 0.99, curr_close * 0.93)

        return Setup(
            symbol="", setup_type="EP", state=state,
            entry=round(entry, 2), stop=round(stop, 2),
            t1=t1, t2=t2, rr=_rr(entry, stop, t2),
            confidence=round(conf, 2), rs_score=0, rs_label="",
            price=round(curr_close, 2),
            pct_change=round((curr_close / float(close.iloc[-2]) - 1) * 100, 2) if len(df) > 1 else 0,
            notes=f"+{round(move_pct*100,1)}% EP · {round(vol_ratio,1)}x vol · {base_bars}d base",
            meta={"ep_move_pct": round(move_pct * 100, 1), "ep_vol_ratio": round(vol_ratio, 1),
                  "base_bars": base_bars, "state": state},
        )
    return None


# ── Tight Base Breakout ────────────────────────────────────────────────────────

def detect_tb(df: pd.DataFrame, max_base_bars: int = 500) -> Setup | None:
    """Flat base ≤8% range, resistance tested ≥2×, volume breakout.
    Supports short bases (10 bars) through multi-year bases (configurable).
    Longer bases get a confidence bonus — they tend to be more explosive.
    """
    if len(df) < 30:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    vol_ma = volume.rolling(50).mean()

    max_bars = min(max_base_bars, len(df) - 3)

    # Adaptive step: fine resolution for short bases, coarser for long ones
    def _step(b: int) -> int:
        if b < 60:
            return 5
        if b < 150:
            return 10
        return 20

    best_setup: Setup | None = None
    best_conf: float = 0.0

    base_bars = 15
    while base_bars <= max_bars:
        ce = len(df) - 2
        cs = ce - base_bars
        if cs < 0:
            break

        seg_high = float(high.iloc[cs: ce + 1].max())
        seg_low = float(low.iloc[cs: ce + 1].min())
        seg_mean = float(close.iloc[cs: ce + 1].mean())
        if seg_mean == 0:
            base_bars += _step(base_bars)
            continue

        range_pct = (seg_high - seg_low) / seg_mean

        # Slightly wider tolerance for very long bases (>1 year)
        max_range = 0.10 if base_bars > 250 else 0.08
        if range_pct > max_range:
            base_bars += _step(base_bars)
            continue

        touches = int((high.iloc[cs: ce + 1] >= seg_high * 0.985).sum())
        if touches < 2:
            base_bars += _step(base_bars)
            continue

        curr_close = float(close.iloc[-1])
        if curr_close <= seg_high:
            base_bars += _step(base_bars)
            continue

        vm = vol_ma.iloc[-1]
        vr = float(volume.iloc[-1] / vm) if not pd.isna(vm) and vm > 0 else 1.0
        if vr < 1.2:
            base_bars += _step(base_bars)
            continue

        target2 = seg_high + (seg_high - seg_low) * 2
        t1 = seg_high + (seg_high - seg_low)
        entry = curr_close
        stop = seg_low * 0.99

        tight = max(0.0, 1.0 - range_pct / max_range)
        touch_s = min(1.0, (touches - 2) / 4.0)
        vol_s = min(1.0, (vr - 1.2) / 2.0)
        # Longer bases get up to +0.08 confidence bonus (Qullamaggie: longer = more explosive)
        duration_bonus = min(0.08, (base_bars - 15) / 500 * 0.08)
        conf = min(0.92, 0.45 + 0.25 * tight + 0.15 * touch_s + 0.15 * vol_s + duration_bonus)

        if conf > best_conf:
            best_conf = conf
            weeks = round(base_bars / 5)
            duration_label = f"{weeks}w" if base_bars < 250 else f"~{round(base_bars/252,1)}yr"
            best_setup = Setup(
                symbol="", setup_type="TB", state="breakout",
                entry=round(entry, 2), stop=round(stop, 2),
                t1=round(t1, 2), t2=round(target2, 2), rr=_rr(entry, stop, target2),
                confidence=round(conf, 2), rs_score=0, rs_label="",
                price=round(curr_close, 2),
                pct_change=round((curr_close / float(close.iloc[-2]) - 1) * 100, 2) if len(df) > 1 else 0,
                notes=f"{duration_label} base · {round(range_pct*100,1)}% tight · {round(vr,1)}x vol",
                meta={"base_bars": base_bars, "range_pct": round(range_pct * 100, 2),
                      "vol_ratio": round(vr, 2), "touches": touches},
            )

        base_bars += _step(base_bars)

    return best_setup


# ── Pocket Pivot ──────────────────────────────────────────────────────────────

def detect_pp(df: pd.DataFrame) -> Setup | None:
    if len(df) < 25:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    ma10 = close.rolling(10).mean()
    ema10 = _ema(close, 10)
    ema20 = _ema(close, 20)
    last = len(df) - 1

    for lookback in range(0, 5):
        idx = last - lookback
        if idx < 12:
            break

        curr = float(close.iloc[idx])
        prev = float(close.iloc[idx - 1])
        vol = float(volume.iloc[idx])

        if curr <= prev:
            continue

        ma = float(ma10.iloc[idx])
        if pd.isna(ma) or curr < ma:
            continue

        e10 = float(ema10.iloc[idx])
        e20 = float(ema20.iloc[idx])
        if pd.isna(e10) or pd.isna(e20) or curr < e10 or e10 < e20 * 0.995:
            continue

        max_down_vol = 0.0
        for j in range(idx - 10, idx):
            if j < 1:
                continue
            if float(close.iloc[j]) < float(close.iloc[j - 1]):
                max_down_vol = max(max_down_vol, float(volume.iloc[j]))

        if max_down_vol <= 0 or vol <= max_down_vol:
            continue

        vol_ratio = vol / max_down_vol
        dist = (curr - e10) / e10
        tight_s = max(0.0, 1.0 - dist / 0.05)
        conf = min(0.88, 0.58 + 0.20 * min(1.0, (vol_ratio - 1.0) / 1.5)
                   + 0.12 * tight_s + (0.05 if lookback == 0 else 0))

        base_lo = float(low.iloc[max(0, idx - 10): idx + 1].min())
        stop = max(base_lo * 0.99, ma * 0.985)
        seg_highs = high.iloc[max(0, idx - 40): idx]
        priors = seg_highs[seg_highs > curr * 1.01]
        t2 = float(priors.iloc[-1]) if not priors.empty else curr * 1.12
        t1 = curr + (t2 - curr) * 0.5

        vol50 = float(volume.iloc[max(0, idx - 50): idx].mean())
        return Setup(
            symbol="", setup_type="PP", state="active",
            entry=round(curr, 2), stop=round(stop, 2),
            t1=round(t1, 2), t2=round(t2, 2), rr=_rr(curr, stop, t2),
            confidence=round(conf, 2), rs_score=0, rs_label="",
            price=round(curr, 2),
            pct_change=round((curr / prev - 1) * 100, 2),
            notes=f"{round(vol_ratio,1)}x down-day vol · {round(dist*100,1)}% from EMA10",
            meta={"vol_vs_down_ratio": round(vol_ratio, 2),
                  "vol_50_ratio": round(vol / vol50, 2) if vol50 > 0 else 0,
                  "bars_ago": lookback},
        )
    return None


# ── EMA Pullback ──────────────────────────────────────────────────────────────

def detect_pull(df: pd.DataFrame) -> Setup | None:
    if len(df) < 30:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    ema21 = _ema(close, 21)
    ema50 = _ema(close, 50)
    rsi = _compute_rsi(close, 14)

    curr_close = float(close.iloc[-1])
    curr_e21 = float(ema21.iloc[-1])
    curr_e50 = float(ema50.iloc[-1])

    if pd.isna(curr_e21) or pd.isna(curr_e50):
        return None
    if curr_close <= curr_e21:
        return None
    if curr_e21 < curr_e50:
        return None

    # EMA21 rising
    e21_10 = float(ema21.iloc[-11]) if len(ema21) > 10 else curr_e21
    if curr_e21 <= e21_10:
        return None

    # Touched EMA21 in last 1-5 bars
    touched = False
    touch_bar = -1
    for lb in range(1, 6):
        i = -(lb + 1)
        if abs(i) > len(df):
            break
        if float(low.iloc[i]) <= float(ema21.iloc[i]) * 1.01:
            touched = True
            touch_bar = lb
            break

    if not touched:
        return None

    rsi_val = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 55.0
    if not (38 <= rsi_val <= 68):
        return None

    conf = 0.62 + (0.08 if touch_bar == 1 else 0.04 if touch_bar <= 2 else 0) + 0.05
    stop = curr_e21 * 0.985
    # Target: next swing high
    swings = high.iloc[-40:]
    targets = swings[swings > curr_close * 1.01]
    t2 = float(targets.iloc[-1]) if not targets.empty else curr_close * 1.10
    t1 = curr_close + (t2 - curr_close) * 0.5

    return Setup(
        symbol="", setup_type="PULL", state="active",
        entry=round(curr_close, 2), stop=round(stop, 2),
        t1=round(t1, 2), t2=round(t2, 2), rr=_rr(curr_close, stop, t2),
        confidence=round(min(0.82, conf), 2), rs_score=0, rs_label="",
        price=round(curr_close, 2),
        pct_change=round((curr_close / float(close.iloc[-2]) - 1) * 100, 2) if len(df) > 1 else 0,
        notes=f"touched EMA21 {touch_bar}d ago · RSI {round(rsi_val,0):.0f}",
        meta={"touch_bars_ago": touch_bar, "ema21": round(curr_e21, 2), "rsi": round(rsi_val, 1)},
    )


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


# ── Weinstein stage ───────────────────────────────────────────────────────────

def weinstein_stage(df: pd.DataFrame) -> int:
    """Classify Weinstein 4-stage cycle using the 150-bar (30-week) SMA.

    Stage 1 — Basing:    flat MA, price below or at MA
    Stage 2 — Advancing: rising MA, price above MA  ← only stage Qullamaggie trades
    Stage 3 — Topping:   flat/rolling MA, price above but MA losing momentum
    Stage 4 — Declining: falling MA, price below MA

    Returns 0 when there is insufficient history.
    """
    if len(df) < 160:
        return 0
    close = df["close"]
    ma150 = close.rolling(150).mean()
    curr_ma = float(ma150.iloc[-1])
    prev_ma = float(ma150.iloc[-11])  # 10-bar slope proxy
    if pd.isna(curr_ma) or pd.isna(prev_ma) or prev_ma == 0:
        return 0
    slope_pct = (curr_ma - prev_ma) / prev_ma * 100
    above_ma = float(close.iloc[-1]) > curr_ma

    if slope_pct > 0.3 and above_ma:
        return 2
    if slope_pct < -0.3 and not above_ma:
        return 4
    if above_ma:
        return 3
    return 1


# ── O'Neill accumulation/distribution day count ───────────────────────────────

def ad_days(df: pd.DataFrame, lookback: int = 25) -> int:
    """Count O'Neill-style institutional accumulation vs distribution days.

    Accumulation day: close up ≥0.2% vs prior, volume > prior bar,
                      close in upper 50% of the day's range.
    Distribution day: close down ≥0.2% vs prior, volume > prior bar.
    Returns net (acc - dist); positive = institutions buying.
    """
    if len(df) < lookback + 2:
        return 0
    tail = df.iloc[-(lookback + 1):]
    acc = dist = 0
    for i in range(1, len(tail)):
        c  = float(tail["close"].iloc[i])
        pc = float(tail["close"].iloc[i - 1])
        v  = float(tail["volume"].iloc[i])
        pv = float(tail["volume"].iloc[i - 1])
        h  = float(tail["high"].iloc[i])
        l  = float(tail["low"].iloc[i])
        if pc <= 0 or pv <= 0:
            continue
        chg = (c - pc) / pc
        bar_range = h - l
        close_pos = (c - l) / bar_range if bar_range > 0 else 0.5
        if chg >= 0.002 and v > pv and close_pos >= 0.5:
            acc += 1
        elif chg <= -0.002 and v > pv:
            dist += 1
    return acc - dist


# ── Overextension penalty ─────────────────────────────────────────────────────

def overextension_penalty(df: pd.DataFrame) -> float:
    """Return a confidence penalty (0–0.20) for overextended price action.

    Conditions:
    - RSI > 80: +0.5 pts per RSI point above 80 (scaled to 0-1 by /100)
    - Price > 8% above EMA21: +0.5 pts per 1% above 8% extension (scaled)
    """
    close = df["close"]
    rsi_series = _compute_rsi(close, 14)
    ema21 = close.ewm(span=21, adjust=False).mean()
    rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 55.0
    curr = float(close.iloc[-1])
    e21 = float(ema21.iloc[-1])

    penalty = 0.0
    if rsi_val > 80:
        penalty += (rsi_val - 80) * 0.005
    if e21 > 0:
        ext = (curr - e21) / e21
        if ext > 0.08:
            penalty += min(0.10, (ext - 0.08) * 0.5)
    return round(min(0.20, penalty), 3)


# ── Failed Breakdown (Bear Trap) ──────────────────────────────────────────────

def detect_fbd(df: pd.DataFrame) -> Setup | None:
    """Failed Breakdown — price breaks below support then snaps back above.

    Classic Qullamaggie/O'Neil bear-trap setup: shorts pile in on the break,
    stock recovers violently as they cover. Entry is on the recovery.

    Detection rules:
    - Support = lowest close in the 20–40 bar window ending 5 bars ago
    - Breakdown: any bar in the last 3–15 bars closed below support by 0.4–6%
    - Recovery: at least one subsequent bar (within 3 bars of breakdown) closes back above support
    - Current close must still be above support
    """
    if len(df) < 55:
        return None

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]
    last   = len(df) - 1

    # Support level: stable floor computed from bars 16–40 bars ago
    # (must sit entirely before the breakdown-scan window so it isn't corrupted
    #  by the breakdown candle itself)
    support_series = close.iloc[last - 40: last - 14]
    if len(support_series) < 5:
        return None
    support = float(support_series.min())

    avg_vol = _avg_vol(volume, last, 50)

    # Scan for the breakdown candle
    for bd_idx in range(last - 15, last - 2):
        if bd_idx < 5:
            continue
        bd_close = float(close.iloc[bd_idx])
        if support <= 0:
            continue
        breakdown_pct = (support - bd_close) / support

        if not (0.004 <= breakdown_pct <= 0.06):
            continue

        # Recovery: closes back above support within 3 bars
        recovered = False
        recovery_idx = -1
        for ri in range(bd_idx + 1, min(bd_idx + 4, last + 1)):
            if float(close.iloc[ri]) > support:
                recovered = True
                recovery_idx = ri
                break

        if not recovered:
            continue

        curr_close = float(close.iloc[last])
        if curr_close <= support:
            continue  # Gave back the recovery

        bd_vol = float(volume.iloc[bd_idx])
        vol_ratio = bd_vol / avg_vol if avg_vol > 0 and not np.isnan(avg_vol) else 1.0

        conf = 0.60
        if breakdown_pct > 0.01:
            conf += 0.06   # Deeper shakeout → more trapped shorts
        if (recovery_idx - bd_idx) == 1:
            conf += 0.06   # Immediate snap-back = very strong rejection
        if vol_ratio > 1.5:
            conf += 0.05   # High-volume breakdown = max trapped

        entry = curr_close
        stop  = float(low.iloc[bd_idx]) * 0.99  # Just below the breakdown wick

        seg_highs = high.iloc[max(0, last - 40): last]
        prior_highs = seg_highs[seg_highs > entry * 1.01]
        t2 = float(prior_highs.iloc[-1]) if not prior_highs.empty else entry * 1.12
        t1 = entry + (t2 - entry) * 0.5

        bars_since = last - bd_idx
        return Setup(
            symbol="", setup_type="FBD", state="active",
            entry=round(entry, 2), stop=round(stop, 2),
            t1=round(t1, 2), t2=round(t2, 2), rr=_rr(entry, stop, t2),
            confidence=round(min(0.82, conf), 2), rs_score=0, rs_label="",
            price=round(curr_close, 2),
            pct_change=round((curr_close / float(close.iloc[-2]) - 1) * 100, 2) if len(df) > 1 else 0,
            notes=f"Bear trap -{round(breakdown_pct*100,1)}% · recovered {bars_since}d ago",
            meta={
                "breakdown_pct": round(breakdown_pct * 100, 2),
                "bars_since": bars_since,
                "bd_vol_ratio": round(vol_ratio, 2),
                "support": round(support, 2),
            },
        )

    return None
