"""OHLCV data fetcher using yfinance with an in-memory cache."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[datetime, pd.DataFrame]] = {}
CACHE_TTL_HOURS = 4


def fetch_ohlcv(symbol: str, period_days: int = 365) -> pd.DataFrame | None:
    """Fetch OHLCV for symbol; returns None on failure."""
    key = f"{symbol}:{period_days}"
    now = datetime.utcnow()
    if key in _cache:
        ts, df = _cache[key]
        if (now - ts).total_seconds() < CACHE_TTL_HOURS * 3600:
            return df

    try:
        end = now
        start = end - timedelta(days=period_days)
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        idx = pd.to_datetime(df.index)
        df.index = idx.tz_convert(None) if idx.tz is not None else idx
        _cache[key] = (now, df)
        return df
    except Exception as e:
        logger.warning("fetch_ohlcv(%s): %s", symbol, e)
        return None


def fetch_batch(symbols: list[str], period_days: int = 365) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = fetch_ohlcv(sym, period_days)
        if df is not None:
            results[sym] = df
    return results


SP500_SAMPLE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "LLY",
    "JPM", "V", "XOM", "JNJ", "MA", "PG", "AVGO", "HD", "CVX", "MRK",
    "ABBV", "COST", "PEP", "KO", "ADBE", "CRM", "WMT", "MCD", "ACN", "TMO",
    "NFLX", "AMD", "QCOM", "TXN", "INTC", "HON", "PM", "CAT", "GE", "BA",
    "INTU", "AMAT", "LRCX", "NOW", "PANW", "SNPS", "KLAC", "MRVL", "ON", "FTNT",
    "ORCL", "IBM", "CSCO", "DELL", "HPQ", "MU", "WDC", "STX", "KEYS", "TRMB",
    "UNP", "CSX", "FDX", "UPS", "DAL", "UAL", "LUV", "AAL", "JBLU", "SAVE",
    "GS", "MS", "BAC", "C", "WFC", "AXP", "BLK", "SCHW", "COF", "USB",
    "CVS", "WBA", "MCK", "ABC", "CAH", "HUM", "CI", "MOH", "CNC", "ELV",
    "NEE", "DUK", "SO", "D", "EXC", "AEP", "SRE", "XEL", "WEC", "ES",
]


def get_universe_symbols(name: str) -> list[str]:
    if name == "sp500":
        return SP500_SAMPLE
    if name == "tech":
        return [s for s in SP500_SAMPLE if s in {
            "AAPL","MSFT","NVDA","GOOGL","META","AVGO","ADBE","CRM","QCOM","TXN",
            "INTC","AMD","AMAT","LRCX","NOW","PANW","SNPS","KLAC","MRVL","FTNT",
            "ORCL","IBM","CSCO","MU","INTU","ON","DELL","HPQ","WDC","STX",
        }]
    return SP500_SAMPLE
