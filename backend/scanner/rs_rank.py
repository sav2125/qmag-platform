"""IBD-style RS score vs SPY."""
from __future__ import annotations

import numpy as np
import pandas as pd

_WINDOWS = {"3m": 63, "6m": 126, "9m": 189, "12m": 252}
_WEIGHTS = {"3m": 0.40, "6m": 0.20, "9m": 0.20, "12m": 0.20}


def _ret(close: pd.Series, bars: int) -> float:
    if len(close) < bars + 1:
        return float("nan")
    s = float(close.iloc[-(bars + 1)])
    e = float(close.iloc[-1])
    return e / s if s > 0 else float("nan")


def rs_score(stock: pd.Series, bench: pd.Series | None = None) -> dict:
    comp = 0.0
    w = 0.0
    periods: dict[str, float] = {}
    for period, bars in _WINDOWS.items():
        sr = _ret(stock, bars)
        if np.isnan(sr):
            continue
        br = _ret(bench, bars) if bench is not None and len(bench) >= bars + 1 else float("nan")
        ratio = sr / br if not np.isnan(br) and br > 0 else sr
        periods[period] = round(ratio, 4)
        comp += _WEIGHTS[period] * ratio
        w += _WEIGHTS[period]

    if w > 0:
        comp /= w
    raw = round(max(0.0, min(100.0, 50.0 + 50.0 * (comp - 1.0))), 1)
    return {"rs_score": round(comp, 4), "rs_raw": raw, **periods}


def rs_label(raw: float) -> str:
    if raw >= 90: return "RS Elite"
    if raw >= 75: return "RS Strong"
    if raw >= 50: return "RS Average"
    if raw >= 25: return "RS Weak"
    return "RS Laggard"


def rank_universe(scores: dict[str, float]) -> dict[str, float]:
    syms = sorted(scores, key=lambda s: scores[s])
    n = len(syms)
    return {s: round((i / (n - 1)) * 99, 1) if n > 1 else 50.0
            for i, s in enumerate(syms)}
