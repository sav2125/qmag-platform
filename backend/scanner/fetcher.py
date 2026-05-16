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
        # Parse dates — Tiingo returns tz-aware ISO strings
        dates = pd.to_datetime(df["date"])
        if dates.dt.tz is not None:
            dates = dates.dt.tz_convert(None)
        df["date"] = dates.dt.normalize()
        df = df.set_index("date").sort_index()
        df = df[~df.index.duplicated(keep="last")]
        # Drop raw (unadjusted) OHLCV before renaming adjusted columns
        df = df.drop(columns=["open", "high", "low", "close", "volume"], errors="ignore")
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


def fetch_ohlcv(symbol: str, period_days: int = 730) -> pd.DataFrame | None:
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

# Nasdaq 100 — growth & tech leaders (QQQ components)
NASDAQ100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX",
    "TMUS", "AMD", "QCOM", "INTU", "AMAT", "ISRG", "TXN", "BKNG", "MRVL", "CMCSA",
    "REGN", "ADI", "PANW", "VRTX", "KLAC", "LRCX", "MU", "SNPS", "CDNS", "CRWD",
    "CEG", "MELI", "FTNT", "MDLZ", "KDP", "CSX", "CTAS", "PCAR", "ORLY", "ROP",
    "ADSK", "MNST", "NXPI", "PAYX", "FAST", "ROST", "DXCM", "IDXX", "EXC", "CTSH",
    "BIIB", "ILMN", "MRNA", "ODFL", "VRSK", "GEHC", "GILD", "FANG", "ANSS", "TTWO",
    "ZS", "TEAM", "DDOG", "NET", "WDAY", "ABNB", "DASH", "TTD", "LULU", "EBAY",
    "DLTR", "FISV", "MCHP", "MAR", "NTAP", "ALGN", "POOL", "ENPH", "OKTA", "SGEN",
    "ON", "GEHC", "GFS", "ARM", "SMCI", "PLTR", "APP", "HOOD", "COIN", "RBLX",
    "DUOL", "SIRI", "WBD", "NWSA", "FOXA", "DKNG", "PINS", "SNAP", "LYFT", "UBER",
]

# Mid Cap Growth — S&P 400 + high-momentum mid caps ($2B–$20B market cap)
MIDCAP_GROWTH = [
    "AXON", "TOST", "CELH", "DUOL", "GTLB", "RDDT", "HIMS", "CAVA", "BROS", "DOCS",
    "SOFI", "UPST", "SEZL", "CRDO", "VRT", "STRL", "POWL", "KTOS", "RKLB", "SPT",
    "TENB", "OSCR", "IRTC", "ACMR", "AEIS", "ACLS", "AEHR", "JOBY", "ASTS", "NNE",
    "DAVE", "MSTR", "IONQ", "QBTS", "RGTI", "RXRX", "VERA", "LMND", "NVTS", "LUNR",
    "TMDX", "ARQT", "NBIS", "PSFE", "WLDN", "YMM", "NRDS", "AI", "SOUN", "BBAI",
    "OPEN", "RKT", "UWMC", "VIAV", "PRCT", "PTON", "BIRD", "XPEV", "NIO", "LI",
    "RIVN", "LCID", "NKLA", "BLNK", "CHPT", "EVGO", "LAZR", "LIDR", "OUST", "VLDR",
    "STEM", "SPWR", "FSLR", "RUN", "NOVA", "SEDG", "ARRY", "BE", "PLUG", "BLDP",
    "MTTR", "RDFN", "OPENDOOR", "UWMC", "GHLD", "PFSI", "IMO", "MQ", "AFRM", "SQ",
    "PYPL", "AFRM", "BILL", "FOUR", "STEP", "RELY", "RPAY", "PAYO", "FLYW", "GPN",
]

# Small Cap Momentum — liquid small caps with momentum potential (<$2B market cap)
SMALLCAP_MOMENTUM = [
    "MARA", "RIOT", "CLSK", "IREN", "BITF", "HUT", "CIFR", "MIGI", "BTBT", "WULF",
    "ACHR", "JOBY", "EVTL", "LILM", "ARCHER", "AAON", "ABCB", "ABMD", "ACAD", "ACBI",
    "ALKT", "ALRM", "ALTR", "AMPH", "AMSF", "AMWD", "ANGI", "AOUT", "APAM", "APLE",
    "APPF", "APPS", "ARES", "ARHS", "ASTH", "ATRC", "ATVI", "AVAV", "AVNT", "AZEK",
    "BANF", "BFAM", "BLBD", "BMBL", "BOOT", "BRBR", "BRKL", "BURL", "CALM", "CALX",
    "CASH", "CDAY", "CENTA", "CERT", "CEVA", "CHCO", "CHRD", "CLFD", "CLNE", "CLPS",
    "CNMD", "CNXC", "COHU", "COLL", "COMP", "COUR", "CPRX", "CRUS", "CSGS", "CTKB",
    "CVCO", "CVLT", "CWST", "DCOM", "DFIN", "DGII", "DIOD", "DJCO", "DNLI", "DORM",
    "DV", "DVAX", "DWAC", "EFC", "EGRX", "EHAB", "ELAN", "ELHC", "ELME", "ELVN",
    "EPAC", "EPAM", "EPRT", "ERAS", "ERIE", "ESE", "ESNT", "EVBG", "EVEX", "EXLS",
]

# All US Equities — combined universe for broadest scan
ALL_US = list(dict.fromkeys(SP500_SAMPLE + NASDAQ100 + MIDCAP_GROWTH + SMALLCAP_MOMENTUM))


def get_universe_symbols(name: str) -> list[str]:
    if name == "sp500":
        return SP500_SAMPLE
    if name == "nasdaq100":
        return NASDAQ100
    if name == "midcap":
        return MIDCAP_GROWTH
    if name == "smallcap":
        return SMALLCAP_MOMENTUM
    if name == "all":
        return ALL_US
    if name == "tech":
        return [s for s in NASDAQ100 if s in {
            "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ADBE", "CRM", "QCOM", "TXN",
            "AMD", "AMAT", "LRCX", "PANW", "SNPS", "KLAC", "MRVL", "FTNT", "CRWD", "DDOG",
            "ZS", "NET", "TEAM", "WDAY", "ON", "MU", "CDNS", "INTU", "PLTR", "APP",
        }]
    return SP500_SAMPLE
