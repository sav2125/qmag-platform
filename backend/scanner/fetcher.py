"""OHLCV data fetcher.

Primary (cloud): Alpaca Markets API — set ALPACA_API_KEY + ALPACA_API_SECRET env vars.
  Free paper trading account at alpaca.markets — no credit card, 200 req/min.
Fallback (local): yfinance — works on localhost, blocked by Yahoo on cloud IPs.

Rate limiting: Alpaca free tier allows 200 req/min. We use:
  - A shared httpx.Client for connection pooling
  - A threading.Semaphore to cap concurrent requests
  - Exponential backoff + full jitter on 429 / 5xx / network errors
  - Retry-After header respected on 429 responses
"""
from __future__ import annotations

import logging
import os
import random
import threading
import time
from datetime import datetime, timedelta

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[datetime, pd.DataFrame]] = {}
CACHE_TTL_HOURS = 4

ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"

# Shared client — reuses TCP connections across threads
_http_client = httpx.Client(timeout=15, limits=httpx.Limits(max_connections=20))

# Semaphore: cap concurrent Alpaca requests to stay under 200 req/min.
# At ~400ms avg latency, 8 workers ≈ 20 req/sec = 1200 req/min — way over.
# 4 concurrent × ~400ms ≈ 10 req/sec = 600 req/min. Still over but 429 backoff handles the rest.
# Adjust _ALPACA_CONCURRENCY down to 2 if you hit 429s frequently.
_ALPACA_CONCURRENCY = int(os.getenv("ALPACA_CONCURRENCY", "4"))
_alpaca_sem = threading.Semaphore(_ALPACA_CONCURRENCY)

_MAX_RETRIES = 4
_BASE_DELAY  = 1.0   # seconds


def _backoff(attempt: int, base: float = _BASE_DELAY, cap: float = 60.0) -> float:
    """Full jitter exponential backoff: sleep = random(0, min(cap, base * 2^attempt))."""
    return random.uniform(0, min(cap, base * (2 ** attempt)))


def _fetch_alpaca(symbol: str, start: str, end: str, api_key: str, api_secret: str) -> pd.DataFrame | None:
    """Fetch adjusted OHLCV from Alpaca with retries, backoff, and jitter."""
    url = ALPACA_DATA_URL.format(symbol=symbol)
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
    }
    params = {
        "timeframe": "1Day",
        "start": start,
        "end": end,
        "adjustment": "all",   # split + dividend adjusted
        "feed": "iex",         # free feed; use "sip" with a paid data plan
        "limit": 10000,
    }

    for attempt in range(_MAX_RETRIES + 1):
        try:
            with _alpaca_sem:
                r = _http_client.get(url, headers=headers, params=params)

            if r.status_code == 429:
                # Respect Retry-After if provided, else use backoff
                retry_after = float(r.headers.get("Retry-After", _backoff(attempt)))
                jitter = random.uniform(0, retry_after * 0.25)
                wait = retry_after + jitter
                logger.warning("Alpaca 429 on %s — waiting %.1fs (attempt %d)", symbol, wait, attempt + 1)
                time.sleep(wait)
                continue

            if r.status_code >= 500:
                wait = _backoff(attempt)
                logger.warning("Alpaca %d on %s — retry in %.1fs", r.status_code, symbol, wait)
                time.sleep(wait)
                continue

            r.raise_for_status()
            bars = r.json().get("bars") or []
            if not bars:
                return None

            df = pd.DataFrame(bars)
            df["t"] = pd.to_datetime(df["t"]).dt.tz_convert(None).dt.normalize()
            df = df.rename(columns={"t": "date", "o": "open", "h": "high",
                                     "l": "low", "c": "close", "v": "volume"})
            df = df.set_index("date").sort_index()
            df = df[~df.index.duplicated(keep="last")]
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            return df

        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            if attempt < _MAX_RETRIES:
                wait = _backoff(attempt)
                logger.warning("Alpaca network error on %s (%s) — retry in %.1fs", symbol, e, wait)
                time.sleep(wait)
            else:
                logger.error("Alpaca fetch(%s) failed after %d retries: %s", symbol, _MAX_RETRIES, e)

        except Exception as e:
            logger.warning("Alpaca fetch(%s): %s", symbol, e)
            return None

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

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    df = _fetch_alpaca(symbol, start, end, api_key, api_secret) if api_key else _fetch_yfinance(symbol, start, end)

    if df is None or len(df) < 20:
        return None

    _cache[key] = (now, df)
    return df


def fetch_batch(symbols: list[str], period_days: int = 365) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for a list of symbols, returning only successful results."""
    results: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = fetch_ohlcv(sym, period_days)
        if df is not None:
            results[sym] = df
    return results


# ---------------------------------------------------------------------------
# Static universe lists
# ---------------------------------------------------------------------------

SP500_SAMPLE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "LLY",
    "JPM", "V", "XOM", "JNJ", "MA", "PG", "AVGO", "HD", "CVX", "MRK",
    "ABBV", "COST", "PEP", "KO", "ADBE", "CRM", "WMT", "MCD", "ACN", "TMO",
    "NFLX", "AMD", "QCOM", "TXN", "INTC", "HON", "PM", "CAT", "GE", "BA",
    "INTU", "AMAT", "LRCX", "NOW", "PANW", "SNPS", "KLAC", "MRVL", "ON", "FTNT",
    "ORCL", "IBM", "CSCO", "DELL", "HPQ", "MU", "WDC", "STX", "KEYS", "TRMB",
    "UNP", "CSX", "FDX", "UPS", "DAL", "UAL", "LUV", "AAL", "JBLU", "NSC",
    "GS", "MS", "BAC", "C", "WFC", "AXP", "BLK", "SCHW", "COF", "USB",
    "CVS", "PFE", "MCK", "COR", "CAH", "HUM", "CI", "MOH", "CNC", "ELV",
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

# S&P 400 Mid-Cap index constituents (~400 real tickers).
# Source: S&P 400 MidCap index as of early 2025.
MIDCAP_GROWTH = [
    # A
    "AAON", "ABG", "ABM", "ACA", "ACHC", "ACM", "ADNT", "AEO", "AFG", "AGCO",
    "AIN", "AIT", "AJG", "AKAM", "ALK", "ALLE", "ALV", "AMAT", "AME", "AMKR",
    "AMN", "AMNB", "AMPH", "AMSF", "AMWD", "ANF", "AOUT", "APAM", "APLE", "APPF",
    "ARCB", "ARW", "ASB", "ASGN", "ASH", "ASTH", "ATI", "ATKR", "ATMU", "ATRC",
    "AVAV", "AVNT", "AXON", "AYI", "AZZ",
    # B
    "BALY", "BANF", "BCPC", "BCO", "BECN", "BFH", "BFAM", "BJ", "BLBD", "BMI",
    "BOOT", "BOX", "BRBR", "BRKL", "BRP", "BUR", "BURL",
    # C
    "CABO", "CACI", "CALM", "CALX", "CARG", "CBT", "CDAY", "CDW", "CENT", "CENTA",
    "CEVA", "CHCO", "CHDN", "CHE", "CHRD", "CIR", "CLD", "CLFD", "CLH", "CLNE",
    "CNX", "CNXC", "COHU", "COLL", "COLM", "COMP", "COOP", "COPART", "COUR",
    "CPRX", "CRUS", "CSGS", "CSWI", "CTLP", "CVCO", "CVLT", "CW", "CWT", "CWST",
    # D
    "DAN", "DCOM", "DDS", "DECK", "DFIN", "DGII", "DKS", "DIOD", "DORM",
    "DV", "DVAX",
    # E
    "EAT", "EEFT", "EFC", "EGRX", "ELAN", "ELF", "ENVA", "EPAC", "EPRT",
    "ERIE", "ESE", "ESNT", "ETSY", "EVBG", "EXLS", "EXPO",
    # F
    "FBIN", "FBP", "FCFS", "FCN", "FELE", "FFIN", "FIBK", "FIVE", "FIVN", "FLO",
    "FLS", "FNB", "FORM", "FR", "FRPT", "FULT", "FUN",
    # G
    "GATX", "GKOS", "GLOB", "GMS", "GNTX", "GPOR", "GPI", "GRBK", "GTLS",
    "GVA", "GXO",
    # H
    "HAE", "HAFC", "HALO", "HBI", "HCSG", "HGV", "HIW", "HLI", "HLNE", "HNI",
    "HOG", "HOPE", "HPP", "HRI", "HRLY", "HURN",
    # I
    "IBP", "IBOC", "ICFI", "IIIN", "IMKTA", "INN", "INSW", "IOSP", "IPGP",
    "ITGR", "ITT", "IVZ",
    # J
    "JACK", "JHG", "JJSF", "JOBY", "JOUT",
    # K
    "KBH", "KBR", "KELYA", "KFY", "KNX", "KRC", "KTB",
    # L
    "LAD", "LANC", "LBRT", "LCII", "LDOS", "LEA", "LGND", "LKFN", "LNC", "LNW",
    "LOPE", "LPX", "LRN", "LSI", "LTC", "LUMN",
    # M
    "MATX", "MBC", "MDGL", "MDU", "MEDP", "MEI", "MKTX", "MLI", "MMSI", "MNKD",
    "MOG", "MPWR", "MRC", "MSA", "MSCI", "MTH", "MTRN", "MTX", "MWA",
    # N
    "NATL", "NBHC", "NEOG", "NFBK", "NFLX", "NHI", "NNN", "NOVT", "NRC",
    "NRDS", "NVT", "NXRT",
    # O
    "OFG", "OGS", "OMCL", "OMF", "OPK", "OPOF", "OSK", "OUST", "OWL",
    # P
    "PAG", "PBH", "PCRX", "PDCO", "PENN", "PFSI", "PJT", "PKE", "PLXS", "PNFP",
    "PODD", "POWL", "PRCT", "PRIM", "PRK", "PSMT", "PSN", "PTGX",
    # R
    "RBCAA", "RCM", "RDNT", "REXR", "RGLD", "RMAX", "RMBS", "RNR", "ROIC",
    "ROLL", "RPRX", "RRC", "RRGB", "RRX", "RUSHA",
    # S
    "SABR", "SAH", "SAIA", "SANM", "SASR", "SBH", "SBRA", "SCSC", "SEIC", "SEM",
    "SFBS", "SFNC", "SHO", "SHOO", "SITE", "SLGN", "SLM", "SM", "SMBC",
    "SMBK", "SMTC", "SNV", "SPSC", "SRC", "SRI", "SRPT", "SSB", "STAG", "STFC",
    "STGW", "STRL", "SUM", "SUPN", "SWX",
    # T
    "TAST", "TBBK", "TDC", "TDOC", "TENB", "THC", "TNET", "TOWN", "TPH", "TPX",
    "TRMK", "TRNO", "TRU", "TRUP", "TWI", "TXNM", "TYL",
    # U
    "UFPI", "UGI", "UMBF", "UNFI", "UNIT", "UPST", "USCF", "USPH",
    # V
    "VAXX", "VBTX", "VG", "VICR", "VLY", "VMI", "VRTS", "VVV",
    # W
    "WAFD", "WAFD", "WDFC", "WHD", "WINA", "WK", "WLDN", "WMS", "WOR", "WSC", "WSM",
    "WTFC", "WTS",
    # X / Y / Z
    "XHR", "XPEL", "YETI", "ZWS",
]

# Russell 2000 / small-cap names — liquid names with momentum potential.
# ~250 real small-cap tickers drawn from Russell 2000 components and active traders.
SMALLCAP_MOMENTUM = [
    # Crypto miners / blockchain
    "MARA", "RIOT", "CLSK", "IREN", "BITF", "HUT", "CIFR", "WULF", "BTBT", "MIGI",
    # eVTOL / air mobility
    "ACHR", "JOBY", "LILM", "EVTL",
    # Biotech / specialty pharma
    "ACAD", "ACBI", "ACHC", "ACET", "ACLS", "AEHR", "AGIO", "AKBA", "ALKT",
    "ALRM", "ALTO", "AMPH", "AMRN", "AMSF", "ANGI", "ANIP", "AQST", "ARDX",
    "ARQT", "ARRY", "ASTH", "ATRC", "AVAV", "AVNT",
    # Banks / financials
    "BANF", "BFAM", "BRKL", "BSVN", "CBTX", "CHCO", "CIVB", "CLBK", "CNOB",
    "DCOM", "EVBN", "FBIZ", "FFBC", "FISI", "FMAO", "FNLC", "FSBW", "FXNC",
    "GBNK", "GNTY", "HAFC", "HBCP", "HFWA", "HOPE", "HTBK", "HVBC",
    # Industrials / manufacturing
    "AAON", "ABM", "ACMR", "AEIS", "AFG", "AIMC", "AMWD", "APAM", "ARCB",
    "ARCH", "ASB", "ASGN", "BCO", "BLBD", "BMI", "BOOT", "BRBR",
    # Technology / software
    "ALTR", "APPF", "APPS", "CDAY", "CERT", "CEVA", "CLFD", "CNXC", "COHU",
    "COLL", "COMP", "COUR", "CPRX", "CRUS", "CSGS", "CTLP", "CVLT",
    # Consumer / retail
    "AOUT", "BIRD", "BMBL", "BURL", "CALM", "CALX", "CASH", "CENTA", "CHRD",
    "CLNE", "CLPS", "CNMD", "COLL", "COLM", "DORM", "DV", "DVAX",
    # Energy / cleantech
    "ARRY", "BE", "BLDP", "BLNK", "CHPT", "EVGO", "FSLR", "NOVA", "PLUG",
    "RUN", "SEDG", "SPWR", "STEM",
    # REITs / real estate
    "APLE", "EPRT", "ESNT", "NXRT", "ROIC", "SBRA", "STAG", "XHR",
    # Healthcare / medical devices
    "ABMD", "ATRC", "ATVI", "AVAV", "AXNX", "BEAT", "BNGO", "DOCS",
    "EGRX", "ELAN", "IRTC", "LMND", "MMSI", "NOVT", "OSCR", "PCRX",
    "PODD", "PRCT", "TMDX",
    # Misc small-caps with high momentum history
    "AFRM", "AI", "ALKT", "ASTS", "BBAI", "BIRD", "BROS", "CAVA", "CELH",
    "CRDO", "DAVE", "DOCS", "DUOL", "FOUR", "GTLB", "HIMS", "HOOD", "IONQ",
    "KTOS", "LMND", "LUNR", "MARA", "MSTR", "NBIS", "NNE", "NVTS", "OPEN",
    "OSCR", "PLTR", "POWL", "QBTS", "RDDT", "RGTI", "RKLB", "RXRX", "SEZL",
    "SMCI", "SOFI", "SOUN", "SPWR", "STRL", "TENB", "TMDX", "TOST", "UPST",
    "VERA", "VRT", "WLDN", "YMM",
    # Additional Russell 2000 names
    "ABCB", "AEIS", "ALRM", "AMPH", "AMSF", "AMWD", "AOUT", "APAM",
    "BALY", "BCPC", "BFH", "BLBD", "BMBL", "BRBR", "BRKL",
    "CABO", "CALM", "CALX", "CASH", "CDAY", "CENTA", "CERT", "CEVA",
    "CHCO", "CLFD", "CLNE", "CNMD", "CNXC", "COHU", "COLL", "COMP",
    "COUR", "CPRX", "CRUS", "CSGS", "CVCO", "CVLT", "CWST",
    "DCOM", "DFIN", "DGII", "DIOD", "DJCO", "DNLI",
    "EFC", "ELAN", "EPAC", "EPRT", "ESE", "ESNT",
    "FBIN", "FBP", "FCFS", "FFIN", "FIBK", "FIVE", "FIVN", "FLO",
    "GATX", "GKOS", "GLOB", "GNTX",
    "HAE", "HAFC", "HALO", "HBI",
    "IBP", "IBOC", "ICFI", "IIIN",
    "JJSF", "JOUT",
    "KBH", "KELYA", "KFY",
    "LANC", "LBRT", "LGND", "LKFN",
    "MATX", "MDU", "MEDP", "MEI", "MMSI",
    "NBHC", "NEOG", "NHI",
    "OFG", "OGS", "OMF",
    "PNFP", "PODD", "PSMT",
    "RBCAA", "RDNT", "RMBS",
    "SABR", "SASR", "SBH", "SBRA", "SCSC", "SEIC", "SFBS",
    "SLGN", "SLM", "SM", "SMBC", "SNBR", "SNV", "SPSC", "SSB",
    "TBBK", "TDC", "TNET", "TOWN", "TRMK",
    "UFPI", "UGI", "UMBF", "UNFI",
    "VLY", "VMI",
    "WAFD", "WHD", "WINA", "WK", "WOR", "WSC", "WTFC",
    "XPEL", "YETI",
]


# ---------------------------------------------------------------------------
# S&P 500 full constituents — fetched from Wikipedia, cached 24 h
# ---------------------------------------------------------------------------

# GitHub-hosted CSV of current S&P 500 constituents (datasets/s-and-p-500-companies repo).
# This CSV is updated within a few days of any index change and is reliably accessible
# from cloud hosts (unlike Wikipedia which blocks server IPs).
_SP500_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies"
    "/main/data/constituents.csv"
)
_sp500_cache: dict = {"symbols": [], "ts": None}


def _fetch_sp500_github() -> list[str]:
    """Fetch the full S&P 500 constituent list from a public GitHub CSV (~503 tickers).

    Dots in tickers (e.g. BRK.B) are converted to hyphens (BRK-B) to match
    the Alpaca / internal convention.

    Returns an empty list on any failure so callers can fall back gracefully.
    """
    try:
        import io as _io
        r = _http_client.get(_SP500_CSV_URL, follow_redirects=True)
        r.raise_for_status()
        df = pd.read_csv(_io.StringIO(r.text))
        symbols = (
            df["Symbol"]
            .str.replace(".", "-", regex=False)
            .str.strip()
            .tolist()
        )
        logger.info("GitHub S&P 500 CSV fetch: %d symbols", len(symbols))
        return symbols
    except Exception as exc:
        logger.warning("_fetch_sp500_github failed: %s", exc)
        return []


def get_sp500_symbols() -> list[str]:
    """Return the full S&P 500 constituent list, refreshed every 24 hours.

    Falls back to the hardcoded SP500_SAMPLE (~100 stocks) if Wikipedia
    is unreachable.
    """
    global _sp500_cache  # noqa: PLW0603

    now = datetime.utcnow()
    cached_ts = _sp500_cache["ts"]
    if cached_ts is not None and (now - cached_ts) < timedelta(hours=24):
        return _sp500_cache["symbols"]

    symbols = _fetch_sp500_github()
    if not symbols:
        logger.info("get_sp500_symbols: using static fallback (%d symbols)", len(SP500_SAMPLE))
        symbols = SP500_SAMPLE

    _sp500_cache["symbols"] = symbols
    _sp500_cache["ts"] = now
    return symbols


# ---------------------------------------------------------------------------
# Derived sets used for universe filtering
# ---------------------------------------------------------------------------

# Large-cap universe: full S&P 500 + Nasdaq 100 (populated at first call to
# get_universe_symbols so the cache can be populated once at startup).
# We seed it with the static sample now; get_universe_symbols("largecap") will
# refresh from the live SP500 list at runtime.
_KNOWN_LARGE: set[str] = set(SP500_SAMPLE + NASDAQ100)

# Mid-cap universe: all symbols in the S&P 400 list.
_KNOWN_MID: set[str] = set(MIDCAP_GROWTH)

# Static fallback used when no Alpaca credentials are configured.
# Deduplication preserves order via dict.fromkeys.
_FALLBACK_ALL: list[str] = list(
    dict.fromkeys(SP500_SAMPLE + NASDAQ100 + MIDCAP_GROWTH + SMALLCAP_MOMENTUM)
)


# ---------------------------------------------------------------------------
# Live Alpaca universe fetcher
# ---------------------------------------------------------------------------

ALPACA_ASSETS_URL = "https://paper-api.alpaca.markets/v2/assets"

# Exchanges considered "US equity" for our purposes.
_US_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "ARCA", "BATS"}

# Module-level cache for the live symbol list.
# Structure: {"symbols": list[str], "ts": datetime | None}
_universe_cache: dict = {"symbols": [], "ts": None}


def _fetch_alpaca_universe(api_key: str, api_secret: str) -> list[str]:
    """Fetch the full list of active, tradable US equity symbols from Alpaca.

    Uses the shared _http_client for connection pooling.
    Filters to:
      - tradable == True
      - exchange in _US_EXCHANGES
      - symbol is purely alphabetic (no hyphens/digits) and 1–5 chars long

    Returns a sorted list of symbol strings, or [] on any error.
    """
    try:
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
        params = {
            "status": "active",
            "asset_class": "us_equity",
        }
        r = _http_client.get(ALPACA_ASSETS_URL, headers=headers, params=params)
        r.raise_for_status()
        assets = r.json()

        symbols = [
            a["symbol"]
            for a in assets
            if a.get("tradable") is True
            and a.get("exchange") in _US_EXCHANGES
            and a.get("symbol", "").isalpha()
            and 1 <= len(a.get("symbol", "")) <= 5
        ]
        return sorted(set(symbols))

    except Exception as exc:
        logger.warning("_fetch_alpaca_universe failed: %s", exc)
        return []


def get_all_us_symbols() -> list[str]:
    """Return a broad list of tradable US equity symbols.

    Caches the result for 24 hours to avoid hammering the Alpaca assets
    endpoint on every scan.  Falls back to the static _FALLBACK_ALL list
    when no API credentials are configured or the fetch fails.
    """
    global _universe_cache  # noqa: PLW0603 — intentional module-level state

    now = datetime.utcnow()
    cached_ts = _universe_cache["ts"]
    if cached_ts is not None and (now - cached_ts) < timedelta(hours=24):
        return _universe_cache["symbols"]

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")

    if api_key and api_secret:
        symbols = _fetch_alpaca_universe(api_key, api_secret)
    else:
        symbols = []

    if not symbols:
        # Either no key set or the fetch failed — use our curated static list.
        logger.info("get_all_us_symbols: using static fallback (%d symbols)", len(_FALLBACK_ALL))
        symbols = _FALLBACK_ALL

    _universe_cache["symbols"] = symbols
    _universe_cache["ts"] = now
    return symbols


# ---------------------------------------------------------------------------
# Public universe selector
# ---------------------------------------------------------------------------

def get_universe_symbols(name: str) -> list[str]:
    """Return a list of symbols for the named universe.

    Supported names:
      "sp500"     — Full S&P 500 constituents (~503 stocks, from Wikipedia)
      "nasdaq100" — QQQ / Nasdaq 100 components
      "midcap"    — S&P 400 mid-cap constituents (~369 symbols)
      "smallcap"  — All live symbols excluding large- and mid-cap sets
      "largecap"  — Full S&P 500 + Nasdaq 100
      "all"       — Full live universe from Alpaca (or static fallback)
      "tech"      — 30-stock tech subset of NASDAQ100
      default     — Full S&P 500
    """
    if name == "sp500":
        return get_sp500_symbols()

    if name == "nasdaq100":
        return NASDAQ100

    if name == "midcap":
        return MIDCAP_GROWTH

    if name == "largecap":
        # Refresh _KNOWN_LARGE with the live S&P 500 list before filtering.
        live_sp500 = get_sp500_symbols()
        return list(set(live_sp500 + NASDAQ100))

    if name == "smallcap":
        # Pull the broadest available universe and strip out large/mid caps
        # so we get genuine small-cap names only.
        live_sp500 = get_sp500_symbols()
        known_large = set(live_sp500 + NASDAQ100)
        all_syms = get_all_us_symbols()
        return [s for s in all_syms if s not in known_large and s not in _KNOWN_MID]

    if name == "all":
        return get_all_us_symbols()

    if name == "tech":
        # 30-stock tech subset drawn from NASDAQ100 constituents.
        _TECH_SET = {
            "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ADBE", "CRM", "QCOM", "TXN",
            "AMD", "AMAT", "LRCX", "PANW", "SNPS", "KLAC", "MRVL", "FTNT", "CRWD", "DDOG",
            "ZS", "NET", "TEAM", "WDAY", "ON", "MU", "CDNS", "INTU", "PLTR", "APP",
        }
        return [s for s in NASDAQ100 if s in _TECH_SET]

    # Default fallback
    return get_sp500_symbols()
