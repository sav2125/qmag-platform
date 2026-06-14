"""Event-driven, no-lookahead backtester for the Qullamaggie setup detectors.

Adopts the rigor from the IBKR-style backtesting methodology:
  - a deliberate test window spanning bull AND bear regimes (default the article's
    2022-01-01 → 2025-04-30: two bear markets + low-vol and high-vol bull runs);
  - a full performance-metric battery (win rate, reward:risk, Sharpe, Sortino,
    max drawdown, streaks, "win 3 of 4" probability, alpha vs SPY, …);
  - TWO exit policies per signal — a fixed N-day calendar hold AND the detector's
    own stop/target — so we see if active management helps;
  - an OVERFITTING guard: every metric is reported not just for the whole window
    but split by regime (bull/bear) and by calendar year, and a setup only "passes"
    if it clears the bar in EVERY sub-period (≥10% annualised, ≥55% monthly win
    rate, max drawdown < a cap), with a minimum sample size.

No-lookahead discipline: at each bar i a detector only ever sees df.iloc[:i+1].
Fills are at the signal bar's close (what you could actually transact on the close
you saw the signal). This is an offline research tool (slow on big universes) —
run it as a script, not on the request path.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .fetcher import fetch_ohlcv
from .patterns import (
    detect_ep, detect_tb, detect_pp, detect_pull, detect_fbd, detect_wys, detect_vcp,
)

logger = logging.getLogger(__name__)

# Detector registry — name → callable taking a point-in-time DataFrame.
DETECTORS = {
    "EP":   lambda d: detect_ep(d),
    "TB":   lambda d: detect_tb(d, max_base_bars=300),
    "VCP":  lambda d: detect_vcp(d, max_base_bars=300),
    "WYS":  lambda d: detect_wys(d),
    "PP":   lambda d: detect_pp(d),
    "PULL": lambda d: detect_pull(d),
    "FBD":  lambda d: detect_fbd(d),
}

# Robustness gate (the article's borderline bar).
GATE_ANNUAL_RET = 10.0   # ≥ 10% annualised
GATE_MONTH_WR   = 55.0   # ≥ 55% of months profitable
GATE_MAX_DD     = 25.0   # max drawdown under this cap (looser than per-trade 10%)
MIN_OBS         = 20     # minimum trades for a result to count


@dataclass
class Trade:
    symbol:     str
    setup:      str
    entry_date: pd.Timestamp
    exit_date:  pd.Timestamp
    entry:      float
    ret_hold:   float          # % return, fixed N-day hold
    ret_tpsl:   float          # % return, detector stop/target exit
    bars_held:  float
    regime:     str            # "bull" | "bear"
    spy_ret:    float          # SPY % return over the same hold (for alpha)
    confidence: float


# ── Trade simulation ──────────────────────────────────────────────────────────

def _simulate(df: pd.DataFrame, i: int, entry: float, stop: float, target: float,
              hold: int) -> tuple[float, float, int, int]:
    """Return (ret_hold%, ret_tpsl%, bars_held, exit_idx) starting from bar i.

    ret_hold  — exit at the close `hold` bars later.
    ret_tpsl  — exit when low ≤ stop (loss) or high ≥ target (win), else at `hold`.
    """
    n = len(df)
    hi = df["high"].values
    lo = df["low"].values
    cl = df["close"].values

    hold_idx = min(i + hold, n - 1)
    ret_hold = (cl[hold_idx] - entry) / entry * 100

    ret_tpsl = ret_hold
    bars = hold_idx - i
    exit_idx = hold_idx
    for j in range(i + 1, hold_idx + 1):
        if lo[j] <= stop:
            ret_tpsl = (stop - entry) / entry * 100
            bars, exit_idx = j - i, j
            break
        if hi[j] >= target:
            ret_tpsl = (target - entry) / entry * 100
            bars, exit_idx = j - i, j
            break
    return ret_hold, ret_tpsl, bars, exit_idx


# ── Regime labelling (SPY 200-SMA trend) ──────────────────────────────────────

def _spy_context(start: str, end: str):
    """Return (spy_df, regime_series) — bull when SPY > rising 200-SMA, else bear."""
    spy = fetch_ohlcv("SPY", period_days=2200)
    if spy is None or len(spy) < 220:
        return None, None
    sma200 = spy["close"].rolling(200).mean()
    rising = sma200 > sma200.shift(20)
    regime = pd.Series(
        np.where((spy["close"] > sma200) & rising, "bull", "bear"),
        index=spy.index,
    )
    return spy, regime


# ── Core backtest ─────────────────────────────────────────────────────────────

def backtest(symbols: list[str], start: str = "2022-01-01", end: str = "2025-04-30",
             hold: int = 20, cooldown: int = 20) -> dict:
    """Run the no-lookahead backtest across `symbols`. Returns a results dict."""
    spy, regime = _spy_context(start, end)
    spy_close = spy["close"] if spy is not None else None
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)

    trades: list[Trade] = []
    for sym in symbols:
        df = fetch_ohlcv(sym, period_days=2200)
        if df is None or len(df) < 250:
            continue
        idxs = [k for k, ts in enumerate(df.index) if start_ts <= ts <= end_ts]
        if not idxs:
            continue

        cool_until = -1
        for i in idxs:
            if i <= cool_until or i < 220:        # warmup + cooldown
                continue
            window = df.iloc[: i + 1]
            best = None
            for name, fn in DETECTORS.items():
                try:
                    s = fn(window)
                except Exception:
                    s = None
                if s is None or s.entry <= 0 or s.stop <= 0 or s.t1 <= s.entry:
                    continue
                if best is None or s.confidence > best[1].confidence:
                    best = (name, s)
            if best is None:
                continue

            name, s = best
            entry = float(df["close"].iloc[i])
            rh, rt, bars, exit_idx = _simulate(df, i, entry, s.stop, s.t1, hold)
            edate, xdate = df.index[i], df.index[exit_idx]

            spy_ret = 0.0
            if spy_close is not None and edate in spy_close.index:
                try:
                    se = float(spy_close.loc[edate])
                    sx_idx = spy_close.index.get_indexer([xdate], method="nearest")[0]
                    sx = float(spy_close.iloc[sx_idx])
                    spy_ret = (sx - se) / se * 100 if se > 0 else 0.0
                except Exception:
                    pass

            reg = "bull"
            if regime is not None and edate in regime.index:
                reg = str(regime.loc[edate])

            trades.append(Trade(
                symbol=sym, setup=name, entry_date=edate, exit_date=xdate,
                entry=entry, ret_hold=round(rh, 2), ret_tpsl=round(rt, 2),
                bars_held=bars, regime=reg, spy_ret=round(spy_ret, 2),
                confidence=s.confidence,
            ))
            cool_until = i + cooldown

    return {
        "window": {"start": start, "end": end, "hold_days": hold},
        "n_trades": len(trades),
        "overall": _report(trades),
        "by_setup": {k: _report([t for t in trades if t.setup == k]) for k in DETECTORS},
        "by_regime": {r: _report([t for t in trades if t.regime == r]) for r in ("bull", "bear")},
        "by_year": _by_year(trades),
        "gate": _gate(trades),
        "trades": [t.__dict__ for t in trades],
    }


# ── Metric battery ────────────────────────────────────────────────────────────

def _binom_3of4(p: float) -> float:
    """P(≥3 wins in 4 i.i.d. trades) given per-trade win prob p."""
    return round((4 * p**3 * (1 - p) + p**4) * 100, 1)


def _max_drawdown(rets: list[float]) -> float:
    """Max drawdown (%) of the compounded equity curve from sequential trades."""
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= (1 + r / 100)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return round(abs(mdd) * 100, 1)


def _streaks(rets: list[float]) -> tuple[int, int]:
    win = loss = mw = ml = 0
    for r in rets:
        if r > 0:
            win += 1; loss = 0
        else:
            loss += 1; win = 0
        mw, ml = max(mw, win), max(ml, loss)
    return mw, ml


def _metrics(rets: list[float], dates: list, spy_rets: list[float], mode: str) -> dict:
    n = len(rets)
    if n == 0:
        return {"mode": mode, "n": 0}
    arr = np.array(rets)
    wins = arr[arr > 0]
    losses = arr[arr <= 0]
    wr = len(wins) / n
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    std = float(arr.std(ddof=1)) if n > 1 else 0.0
    downside = arr[arr < 0]
    dstd = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0

    # Years spanned (for annualisation) from entry dates.
    yrs = 1.0
    if dates:
        span_days = (max(dates) - min(dates)).days
        yrs = max(span_days / 365.25, 0.25)
    cum = float(np.prod(1 + arr / 100) - 1)            # reinvested
    annualised = ((1 + cum) ** (1 / yrs) - 1) * 100 if cum > -1 else -100.0

    # Win rate by month
    monthly: dict[str, float] = {}
    for r, d in zip(rets, dates):
        key = f"{d.year}-{d.month:02d}"
        monthly[key] = monthly.get(key, 0.0) + r
    month_wr = (sum(1 for v in monthly.values() if v > 0) / len(monthly) * 100) if monthly else 0.0

    mw, ml = _streaks(rets)
    alpha = float((arr - np.array(spy_rets)).mean()) if spy_rets else 0.0

    return {
        "mode":            mode,
        "n":               n,
        "win_rate":        round(wr * 100, 1),
        "avg_win":         round(avg_win, 2),
        "avg_loss":        round(avg_loss, 2),
        "expectancy":      round(float(arr.mean()), 2),
        "reward_risk":     round(avg_win / abs(avg_loss), 2) if avg_loss < 0 else None,
        "total_1k":        round(float((arr / 100 * 1000).sum()), 0),   # $1k per trade
        "cum_return":      round(cum * 100, 1),
        "annualised":      round(annualised, 1),
        "sharpe":          round(float(arr.mean()) / std, 2) if std > 0 else None,   # per-trade
        "sortino":         round(float(arr.mean()) / dstd, 2) if dstd > 0 else None,
        "max_drawdown":    _max_drawdown(rets),
        "month_win_rate":  round(month_wr, 1),
        "max_win_streak":  mw,
        "max_loss_streak": ml,
        "win_3_of_4":      _binom_3of4(wr),
        "alpha_vs_spy":    round(alpha, 2),
        "avg_bars_held":   None,
    }


def _report(trades: list[Trade]) -> dict:
    if not trades:
        return {"n": 0}
    dates = [t.exit_date for t in trades]
    spy = [t.spy_ret for t in trades]
    rep = {
        "n":     len(trades),
        "hold":  _metrics([t.ret_hold for t in trades], dates, spy, "fixed_hold"),
        "tpsl":  _metrics([t.ret_tpsl for t in trades], dates, spy, "stop_target"),
    }
    rep["hold"]["avg_bars_held"] = round(float(np.mean([t.bars_held for t in trades])), 1)
    rep["tpsl"]["avg_bars_held"] = rep["hold"]["avg_bars_held"]
    return rep


def _by_year(trades: list[Trade]) -> dict:
    out = {}
    for y in sorted({t.exit_date.year for t in trades}):
        out[str(y)] = _report([t for t in trades if t.exit_date.year == y])
    return out


def _gate(trades: list[Trade]) -> dict:
    """Per-setup pass/fail: clears the bar in the whole window AND every sub-period."""
    result = {}
    for name in DETECTORS:
        ts = [t for t in trades if t.setup == name]
        if len(ts) < MIN_OBS:
            result[name] = {"pass": False, "reason": f"only {len(ts)} trades (< {MIN_OBS})"}
            continue
        periods = {"overall": ts}
        for r in ("bull", "bear"):
            sub = [t for t in ts if t.regime == r]
            if sub:
                periods[r] = sub
        for y in sorted({t.exit_date.year for t in ts}):
            periods[str(y)] = [t for t in ts if t.exit_date.year == y]

        fails = []
        for label, sub in periods.items():
            if len(sub) < 5:
                continue   # too few to judge a sub-period
            m = _metrics([t.ret_tpsl for t in sub], [t.exit_date for t in sub],
                         [t.spy_ret for t in sub], "stop_target")
            if m["annualised"] < GATE_ANNUAL_RET:
                fails.append(f"{label}: {m['annualised']}% ann")
            elif m["month_win_rate"] < GATE_MONTH_WR:
                fails.append(f"{label}: {m['month_win_rate']}% mo-WR")
            elif m["max_drawdown"] > GATE_MAX_DD:
                fails.append(f"{label}: {m['max_drawdown']}% DD")
        result[name] = {"pass": not fails, "n": len(ts),
                        "reason": "clears every sub-period" if not fails else "; ".join(fails[:4])}
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser(description="Backtest the Qullamaggie setup detectors.")
    ap.add_argument("--symbols", default="NVDA,AAPL,MSFT,AMD,META",
                    help="comma-separated tickers (small universe = faster)")
    ap.add_argument("--start", default="2022-01-01")
    ap.add_argument("--end", default="2025-04-30")
    ap.add_argument("--hold", type=int, default=20)
    ap.add_argument("--json", action="store_true", help="dump full JSON (incl. trades)")
    a = ap.parse_args()

    syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    res = backtest(syms, a.start, a.end, hold=a.hold)

    if a.json:
        print(json.dumps(res, default=str, indent=2))
    else:
        w = res["window"]
        print(f"\nBacktest {w['start']} → {w['end']}  (hold {w['hold_days']}d)  "
              f"{len(syms)} symbols  {res['n_trades']} trades\n")
        def line(label, rep):
            if not rep or rep.get("n", 0) == 0:
                print(f"  {label:<10} n=0"); return
            h, t = rep["hold"], rep["tpsl"]
            print(f"  {label:<10} n={rep['n']:<4} "
                  f"| HOLD wr {h['win_rate']:>5}% ann {h['annualised']:>7}% Sharpe {h['sharpe']} DD {h['max_drawdown']}% "
                  f"| TP/SL wr {t['win_rate']:>5}% ann {t['annualised']:>7}% R:R {t['reward_risk']} DD {t['max_drawdown']}%")
        print("OVERALL"); line("all", res["overall"])
        print("\nBY SETUP"); [line(k, v) for k, v in res["by_setup"].items()]
        print("\nBY REGIME"); [line(k, v) for k, v in res["by_regime"].items()]
        print("\nBY YEAR"); [line(k, v) for k, v in res["by_year"].items()]
        print("\nROBUSTNESS GATE (TP/SL, every sub-period)")
        for k, g in res["gate"].items():
            print(f"  {k:<10} {'PASS' if g['pass'] else 'fail'}  — {g['reason']}")
        print("\n  NOTE: 'ann' (annualised, reinvested) OVERSTATES returns when trades overlap")
        print("  across symbols — read win rate, R:R, expectancy, Sharpe & max DD instead.")
        print("  TP/SL is the realistic exit lens. A Phase-2 portfolio equity curve (shared")
        print("  capital) is needed for a trustworthy annualised/Sharpe number.\n")
