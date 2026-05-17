"""Qullamaggie Platform — FastAPI backend."""
from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Qullamaggie Platform", version="1.0.0")

_extra_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://qmag-platform-1.onrender.com",
    ] + _extra_origins,
    allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHLIST_PATH = Path(__file__).parent / "data" / "watchlist.json"
WATCHLIST_PATH.parent.mkdir(exist_ok=True)


# ── Models ────────────────────────────────────────────────────────────────────

class ScanResult(BaseModel):
    symbol: str
    setup_type: str
    state: str
    entry: float
    stop: float
    t1: float
    t2: float
    rr: float
    confidence: float
    grade: str
    rs_score: float
    rs_label: str
    price: float
    pct_change: float
    notes: str
    meta: dict
    weinstein_stage: int = 0   # 1-4; 0 = insufficient data
    ad_net: int = 0            # O'Neill A/D net days (+ = accumulation)


class WatchlistItem(BaseModel):
    symbol: str


class EmailTestRequest(BaseModel):
    universe: str = "sp500"
    setup: str | None = None
    min_rs: float = 50.0
    top: int = 20


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_watchlist() -> list[str]:
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text())
    return []


def _save_watchlist(symbols: list[str]) -> None:
    WATCHLIST_PATH.write_text(json.dumps(sorted(set(symbols))))


def _setup_to_dict(s) -> dict:
    return {
        "symbol": s.symbol, "setup_type": s.setup_type, "state": s.state,
        "entry": s.entry, "stop": s.stop, "t1": s.t1, "t2": s.t2,
        "rr": s.rr, "confidence": s.confidence, "grade": s.grade,
        "rs_score": s.rs_score, "rs_label": s.rs_label,
        "price": s.price, "pct_change": s.pct_change,
        "notes": s.notes, "meta": s.meta,
        "weinstein_stage": s.weinstein_stage,
        "ad_net": s.ad_net,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "date": date.today().isoformat()}


@app.get("/debug/fetch")
def debug_fetch(symbol: str = "NVDA"):
    """Test the active data fetcher and surface any errors."""
    import traceback
    from scanner.fetcher import _fetch_alpaca, _fetch_yfinance
    from datetime import datetime, timedelta

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    end = datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")

    try:
        if api_key:
            df = _fetch_alpaca(symbol, start, end, api_key, api_secret)
            source = "alpaca"
        else:
            df = _fetch_yfinance(symbol, start, end)
            source = "yfinance"

        if df is None or df.empty:
            return {"error": "empty dataframe", "symbol": symbol, "source": source,
                    "alpaca_key_set": bool(api_key), "alpaca_secret_set": bool(api_secret)}

        return {
            "symbol": symbol,
            "source": source,
            "alpaca_key_set": bool(api_key),
            "rows": len(df),
            "last_close": float(df["close"].iloc[-1]),
            "last_date": str(df.index[-1].date()),
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc(),
                "alpaca_key_set": bool(api_key), "alpaca_secret_set": bool(api_secret)}


@app.get("/scan", response_model=list[ScanResult])
def scan(
    universe: str = Query("sp500", description="sp500 | nasdaq100 | midcap | smallcap | all | tech | watchlist"),
    setup: str | None = Query(None, description="ep | tb | pp | pull | fbd"),
    min_rs: float = Query(50.0, ge=0, le=100),
    min_score: float = Query(0.0, ge=0, le=100),
    top: int = Query(20, ge=1, le=100),
    min_adr: float = Query(0.0, ge=0, le=20, description="Min Average Daily Range %"),
    min_pct_change: float = Query(0.0, ge=0, le=50, description="Min daily % change"),
    above_ema21: bool = Query(False, description="Require price above EMA21"),
    above_ema50: bool = Query(False, description="Require price above EMA50"),
    max_base_bars: int = Query(500, ge=10, le=1500, description="Max TB base length in bars (~5 bars/week)"),
):
    from scanner.engine import scan as run_scan

    symbols_override = None
    if universe == "watchlist":
        syms = _load_watchlist()
        if not syms:
            return []
        symbols_override = syms

    try:
        if symbols_override:
            from scanner.engine import _process_symbol
            from scanner.fetcher import fetch_ohlcv
            from concurrent.futures import ThreadPoolExecutor, as_completed

            spy_df = fetch_ohlcv("SPY")
            spy_close = spy_df["close"] if spy_df is not None else None
            results = []
            with ThreadPoolExecutor(max_workers=10) as ex:
                futs = {
                    ex.submit(
                        _process_symbol, s, setup, spy_close, min_rs, 1.0, 0,
                        min_adr, min_pct_change, above_ema21, above_ema50, max_base_bars,
                    ): s
                    for s in symbols_override
                }
                for fut in as_completed(futs):
                    hit = fut.result()
                    if hit and hit.confidence * 100 >= min_score:
                        results.append(hit)
            results.sort(key=lambda s: (-ord(s.grade[0]), -(s.confidence * s.rs_score)))
            results = results[:top]
        else:
            results = run_scan(
                universe=universe,
                setup_filter=setup,
                min_rs=min_rs,
                min_score=min_score,
                top_n=top,
                min_adr=min_adr,
                min_pct_change=min_pct_change,
                require_above_ema21=above_ema21,
                require_above_ema50=above_ema50,
                max_base_bars=max_base_bars,
            )
    except Exception as e:
        logger.exception("Scan error")
        raise HTTPException(500, str(e))

    return [ScanResult(**_setup_to_dict(r)) for r in results]


@app.get("/watchlist")
def get_watchlist():
    return {"symbols": _load_watchlist()}


@app.post("/watchlist")
def add_to_watchlist(item: WatchlistItem):
    syms = _load_watchlist()
    sym = item.symbol.upper().strip()
    if sym not in syms:
        syms.append(sym)
        _save_watchlist(syms)
    return {"symbols": sorted(set(syms))}


@app.delete("/watchlist/{symbol}")
def remove_from_watchlist(symbol: str):
    syms = _load_watchlist()
    sym = symbol.upper().strip()
    syms = [s for s in syms if s != sym]
    _save_watchlist(syms)
    return {"symbols": syms}


@app.post("/notify/send")
def send_notification(req: EmailTestRequest):
    from scanner.engine import scan as run_scan
    from notifier.email_sender import send_digest

    to_email = os.getenv("NOTIFY_TO_EMAIL")
    from_email = os.getenv("NOTIFY_FROM_EMAIL")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not to_email or not from_email:
        raise HTTPException(400, "Email not configured. Set NOTIFY_TO_EMAIL and NOTIFY_FROM_EMAIL in .env")

    try:
        results = run_scan(
            universe=req.universe,
            setup_filter=req.setup,
            min_rs=req.min_rs,
            top_n=req.top,
        )
        send_digest(results, to_email, from_email, smtp_host, smtp_port, smtp_user, smtp_pass)
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"sent": True, "setups": len(results), "to": to_email}


@app.post("/notify/test")
def test_email():
    """Send a test email with mock data to verify SMTP config."""
    from notifier.email_sender import send_digest
    from scanner.patterns import Setup

    to_email = os.getenv("NOTIFY_TO_EMAIL")
    from_email = os.getenv("NOTIFY_FROM_EMAIL")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not to_email or not from_email:
        raise HTTPException(400, "Email not configured.")

    mock = [
        Setup("NVDA", "EP", "breakout", 148.50, 138.20, 163.40, 178.30, 1.5,
              0.82, 78.0, "RS Strong", 148.50, 1.2, "EP +12% · 5x vol · 8d base"),
        Setup("AAPL", "TB", "breakout", 195.20, 187.50, 210.10, 225.00, 1.9,
              0.71, 68.0, "RS Average", 195.20, 0.4, "20d base · 4.1% tight · 1.8x vol"),
    ]
    try:
        send_digest(mock, to_email, from_email, smtp_host, smtp_port, smtp_user, smtp_pass)
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"sent": True, "to": to_email}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
