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
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "date": date.today().isoformat()}


@app.get("/debug/fetch")
def debug_fetch(symbol: str = "NVDA"):
    """Test yfinance data fetch and one pattern detector."""
    from scanner.fetcher import fetch_ohlcv
    from scanner.patterns import detect_pp
    from scanner.rs_rank import rs_score

    try:
        spy = fetch_ohlcv("SPY")
        df = fetch_ohlcv(symbol)
        if df is None:
            return {"error": "fetch returned None", "symbol": symbol}
        rs = rs_score(df["close"], spy["close"] if spy is not None else None)
        hit = detect_pp(df)
        return {
            "symbol": symbol,
            "rows": len(df),
            "last_close": float(df["close"].iloc[-1]),
            "rs_raw": rs["rs_raw"],
            "pp_detected": hit is not None,
            "index_tz": str(df.index.dtype),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/scan", response_model=list[ScanResult])
def scan(
    universe: str = Query("sp500", description="sp500 | tech | watchlist"),
    setup: str | None = Query(None, description="ep | tb | pp | pull"),
    min_rs: float = Query(50.0, ge=0, le=100),
    min_score: float = Query(0.0, ge=0, le=100),
    top: int = Query(20, ge=1, le=100),
):
    from scanner.engine import scan as run_scan

    effective_universe = universe
    symbols_override = None
    if universe == "watchlist":
        syms = _load_watchlist()
        if not syms:
            return []
        symbols_override = syms

    try:
        if symbols_override:
            from scanner.fetcher import get_universe_symbols
            from scanner.engine import _process_symbol, DETECTORS
            from scanner.fetcher import fetch_ohlcv
            import pandas as pd
            from scanner.rs_rank import rs_score, rs_label
            from concurrent.futures import ThreadPoolExecutor, as_completed

            spy_df = fetch_ohlcv("SPY")
            spy_close = spy_df["close"] if spy_df is not None else None
            results = []
            with ThreadPoolExecutor(max_workers=10) as ex:
                futs = {ex.submit(_process_symbol, s, setup, spy_close, min_rs, 1.0, 0): s
                        for s in symbols_override}
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
