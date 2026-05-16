"""OHLCV data fetcher.

Primary (cloud): Tiingo API — set TIINGO_API_KEY env var.
Fallback (local): yfinance — works on localhost, blocked by Yahoo on cloud IPs.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[datetime, pd.DataFrame]] = {}
CACHE_TTL_HOURS = 4

TIINGO_BASE = "https://api.tiingo.com/tiingo/daily"


def _fetch_tiingo(symbol: str, start: str, end: str, api_key: str) -> pd.DataFrame | None:
    """Fetch OHLCV from Tiingo."""
    url = f"{TIINGO_BASE}/{symbol}/prices"
    headers = {"Content-Type": "application/json"}
    try:
        r = httpx.get(
            url,
            params={"startDate": start, "endDate": end, "token": api_key},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df.set_index("date").sort_index()
        # Use adjusted prices for accurate pattern detection
        df = df.rename(columns={
            "adjOpen": "open", "adjHigh": "high",
            "adjLow": "low", "adjClose": "close", "adjVolume": "volume",
        })
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df
    except Exception as e:
        logger.warning("Tiingo fetch(%s): %s", symbol, e)
        return None


def _fetch_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame | None:
    """Fetch OHLCV from yfinance (works locally, blocked on cloud IPs)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end)
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        idx = pd.to_datetime(df.index)
        df.index = idx.tz_convert(None) if idx.tz is not None else idx
        return df
    except Exception as e:
        logger.warning("yfinance fetch(%s): %s", symbol, e)
        return None


def fetch_ohlcv(symbol: str, period_days: int = 365) -> pd.DataFrame | None:
    """Fetch OHLCV for symbol; returns None on failure."""
    key = f"{symbol}:{period_days}"
    now = datetime.utcnow()
    if key in _cache:
        ts, df = _cache[key]
        if (now - ts).total_seconds() < CACHE_TTL_HOURS * 3600:
            return df

    end = now.strftime("%Y-%m-%d")
    start = (now - timedelta(days=period_days)).strftime("%Y-%m-%d")

    api_key = os.getenv("TIINGO_API_KEY", "")
    df = _fetch_tiingo(symbol, start, end, api_key) if api_key else _fetch_yfinance(symbol, start, end)

    if df is None or len(df) < 20:
        return None

    _cache[key] = (now, df)
    return df


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
            "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ADBE", "CRM", "QCOM", "TXN",
            "INTC", "AMD", "AMAT", "LRCX", "NOW", "PANW", "SNPS", "KLAC", "MRVL", "FTNT",
            "ORCL", "IBM", "CSCO", "MU", "INTU", "ON", "DELL", "HPQ", "WDC", "STX",
        }]
    return SP500_SAMPLE
