"""Main scanning engine: runs all Qullamaggie setups on a universe."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from .fetcher import fetch_ohlcv, fetch_batch, get_universe_symbols
from .patterns import (
    Setup, detect_ep, detect_pp, detect_tb, detect_pull, detect_fbd, detect_wys,
    weinstein_stage, ad_days, overextension_penalty,
    relative_volume, institutional_composite_score, bull_exhaustion_warning,
)
from .analyzer import _resample_weekly, _tf_signals
from .prob_scorer import compute_prob_score
from .rs_rank import rs_score, rs_label, rank_universe

logger = logging.getLogger(__name__)

# Ordered by detection priority — when multiple setups fire on the same symbol,
# the one with the lower priority number wins.
# WYS sits above PP/PULL/FBD because it requires confirmed prior accumulation range.
DETECTORS = [detect_ep, detect_tb, detect_wys, detect_pp, detect_pull, detect_fbd]

SETUP_PRIORITY = {"EP": 0, "TB": 1, "WYS": 2, "PP": 3, "PULL": 3, "FBD": 4, "FLAG": 5}


def _ma_stack_label(df: pd.DataFrame) -> str:
    """Return a compact MA stack label for use by prob_scorer."""
    close = df["close"]
    price = float(close.iloc[-1])
    ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
    ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    above21 = price > ema21
    above50 = price > ema50
    rising21 = ema21 > float(close.ewm(span=21, adjust=False).mean().iloc[-6]) if len(close) >= 6 else True
    if above21 and above50 and rising21:   return "full_bull"
    if above21 and rising21:               return "partial_bull"
    if not above21 and not above50:        return "bear"
    return "mixed"


def _adr(df: pd.DataFrame, lookback: int = 20) -> float:
    """Average Daily Range % — measures how much the stock moves each day."""
    tail = df.tail(lookback)
    ranges = (tail["high"] - tail["low"]) / tail["low"] * 100
    return float(ranges.mean())


def _above_ema(df: pd.DataFrame, period: int) -> bool:
    """True if latest close is above the EMA of given period."""
    ema = df["close"].ewm(span=period, adjust=False).mean()
    return float(df["close"].iloc[-1]) > float(ema.iloc[-1])


def _process_symbol(
    symbol: str,
    setup_filter: str | None,
    spy_close: pd.Series | None,
    min_rs: float,
    min_price: float,
    min_vol: float,
    min_adr: float,
    min_pct_change: float,
    require_above_ema21: bool,
    require_above_ema50: bool,
    max_base_bars: int = 500,
) -> Setup | None:
    # Fetch enough history to cover the max base length + buffer
    period_days = max(730, int(max_base_bars * 1.4) + 60)
    df = fetch_ohlcv(symbol, period_days=period_days)
    if df is None or len(df) < 60:
        return None

    price = float(df["close"].iloc[-1])
    if price < min_price:
        return None

    avg_vol = float(df["volume"].tail(50).mean())
    if avg_vol < min_vol:
        return None

    # ADR filter — minimum daily range % (liquidity / tradability proxy)
    if min_adr > 0 and _adr(df) < min_adr:
        return None

    # EMA trend filters
    if require_above_ema21 and not _above_ema(df, 21):
        return None
    if require_above_ema50 and not _above_ema(df, 50):
        return None

    # Daily % change filter
    if min_pct_change > 0:
        prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else price
        pct_chg = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
        if pct_chg < min_pct_change:
            return None

    # RS filter
    rs = rs_score(df["close"], spy_close)
    raw_rs = rs["rs_raw"]
    if raw_rs < min_rs:
        return None

    # Near 52-week high (within 35%) — Qullamaggie avoids deep laggards unless EP
    high_52 = float(df["high"].tail(252).max())
    pct_off = (high_52 - price) / high_52 if high_52 > 0 else 1.0

    best: Setup | None = None
    for detect in DETECTORS:
        if setup_filter:
            sf = setup_filter.upper()
            type_map = {
                "EP": detect_ep, "TB": detect_tb,
                "PP": detect_pp, "PULL": detect_pull,
                "FBD": detect_fbd, "WYS": detect_wys,
            }
            if detect != type_map.get(sf):
                continue

        try:
            hit = detect(df, max_base_bars=max_base_bars) if detect == detect_tb else detect(df)
        except Exception as e:
            logger.debug("%s detector error on %s: %s", detect.__name__, symbol, e)
            continue

        if hit is None:
            continue

        # EP can override the 35% off-high filter; everything else requires proximity
        if hit.setup_type != "EP" and pct_off > 0.35:
            continue

        if best is None or SETUP_PRIORITY.get(hit.setup_type, 9) < SETUP_PRIORITY.get(best.setup_type, 9):
            best = hit

    if best is None:
        return None

    best.symbol = symbol
    best.rs_score = round(raw_rs, 1)
    best.rs_label = rs_label(raw_rs)

    # ── Enrichment ────────────────────────────────────────────────────────────
    best.weinstein_stage = weinstein_stage(df)
    best.ad_net          = ad_days(df)
    best.rvol            = relative_volume(df)
    best.isc_score       = institutional_composite_score(df)

    # Weekly timeframe direction — free resampling of existing daily bars, no extra API call
    try:
        df_weekly       = _resample_weekly(df)
        wk              = _tf_signals(df_weekly, "Weekly")
        best.weekly_dir = wk.get("direction", "neutral")
    except Exception:
        best.weekly_dir = "neutral"

    # P Score — probability-weighted signal voting (ported from sav2125/technical-analysis)
    try:
        ps = compute_prob_score(
            df=df,
            stage=best.weinstein_stage,
            isc=best.isc_score,
            ad_net=best.ad_net,
            ma_stack=_ma_stack_label(df),
            active_setups=[best],
            weekly_dir=best.weekly_dir,
            rs_score=best.rs_score,
        )
        best.prob_score = ps["prob_score"]
        best.prob_grade = ps["prob_grade"]
    except Exception:
        best.prob_score = 0.0
        best.prob_grade = "D"

    # Overextension penalty: docks confidence when RSI > 80 or price far above EMA21
    penalty = overextension_penalty(df)
    if penalty > 0:
        best.confidence = round(max(0.30, best.confidence - penalty), 2)
        best.meta["overextension_penalty"] = penalty

    # Bull exhaustion warning: appended to notes when RSI > 70 + vol fading + extended
    warning = bull_exhaustion_warning(df)
    if warning:
        best.notes = (best.notes + " · " + warning) if best.notes else warning

    return best


def scan(
    universe: str = "sp500",
    setup_filter: str | None = None,
    min_rs: float = 50.0,
    min_score: float = 0.0,
    top_n: int = 20,
    min_price: float = 5.0,
    min_vol: float = 200_000,
    min_adr: float = 0.0,
    min_pct_change: float = 0.0,
    require_above_ema21: bool = False,
    require_above_ema50: bool = False,
    max_base_bars: int = 500,
) -> list[Setup]:
    symbols = get_universe_symbols(universe)

    # Fetch SPY for RS calculation
    spy_df = fetch_ohlcv("SPY")
    spy_close = spy_df["close"] if spy_df is not None else None

    results: list[Setup] = []

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {
            ex.submit(
                _process_symbol, sym, setup_filter, spy_close,
                min_rs, min_price, min_vol,
                min_adr, min_pct_change,
                require_above_ema21, require_above_ema50,
                max_base_bars,
            ): sym
            for sym in symbols
        }
        for fut in as_completed(futures):
            try:
                hit = fut.result()
                if hit and hit.prob_score >= min_score:
                    results.append(hit)
            except Exception as e:
                logger.debug("scan error %s: %s", futures[fut], e)

    # Sort by P Score descending — the single score (probability-weighted signal voting)
    results.sort(key=lambda s: -s.prob_score)
    return results[:top_n]
