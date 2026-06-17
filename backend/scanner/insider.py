"""Insider buying — open-market Form 4 transactions from SEC EDGAR (free, no key).

Insiders sell for many reasons (diversification, taxes, comp) but they buy on the
open market for exactly one: they think the stock is going up. Cluster buying (several
insiders purchasing in a short window) is one of the better-documented leading signals
in the literature. We read each company's recent Form 4 filings, isolate open-market
purchases (transaction code "P") vs sales ("S"), and weight buys far more than sells.

EDGAR is free and datacenter-friendly (works on Render) but requires a descriptive
User-Agent. Per-symbol result cached 12h; the ticker→CIK map cached 24h.
"""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import requests

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "qmag-platform research siddharthaman@gmail.com"}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUB_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

_TICKER_MAP: dict = {"ts": 0.0, "map": None}
_TICKER_TTL = 24 * 3600
_SYM_CACHE: dict = {}
_SYM_TTL = 12 * 3600
_LOOKBACK_DAYS = 120
_MAX_FILINGS = 30


def _ticker_map():
    now = time.time()
    if _TICKER_MAP["map"] and now - _TICKER_MAP["ts"] < _TICKER_TTL:
        return _TICKER_MAP["map"]
    try:
        data = requests.get(_TICKERS_URL, headers=_UA, timeout=15).json()
        m = {row["ticker"].upper(): str(row["cik_str"]) for row in data.values()}
        _TICKER_MAP.update(ts=now, map=m)
        return m
    except Exception:
        logger.exception("EDGAR ticker map fetch failed")
        return _TICKER_MAP["map"]


def _parse_form4(cik: str, acc_nodash: str, doc: str):
    """Fetch + parse one Form 4 XML → reporter + open-market transactions."""
    try:
        r = requests.get(_DOC_URL.format(cik=cik, acc=acc_nodash, doc=doc), headers=_UA, timeout=15)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.content)
    except Exception:
        return None
    owner = (root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or "Insider").strip()
    rel = ".//reportingOwner/reportingOwnerRelationship/"
    is_dir = (root.findtext(rel + "isDirector") or "").strip() in ("1", "true")
    is_off = (root.findtext(rel + "isOfficer") or "").strip() in ("1", "true")
    title = (root.findtext(rel + "officerTitle") or "").strip() or \
            ("Director" if is_dir else "Officer" if is_off else "10% owner")
    txns = []
    for t in root.findall(".//nonDerivativeTransaction"):
        code = (t.findtext("./transactionCoding/transactionCode") or "").strip()
        if code not in ("P", "S"):       # only open-market purchases / sales
            continue
        try:
            shares = float(t.findtext("./transactionAmounts/transactionShares/value") or 0)
            price = float(t.findtext("./transactionAmounts/transactionPricePerShare/value") or 0)
        except ValueError:
            continue
        txns.append({"code": code, "shares": shares, "price": price,
                     "date": t.findtext("./transactionDate/value")})
    if not txns:
        return None
    return {"owner": owner, "title": title, "txns": txns}


def get_insider(symbol: str) -> dict | None:
    symbol = symbol.upper().strip()
    now = time.time()
    cached = _SYM_CACHE.get(symbol)
    if cached and now - cached[0] < _SYM_TTL:
        return cached[1]

    tmap = _ticker_map()
    if not tmap or symbol not in tmap:
        return None
    cik = tmap[symbol]
    cik10 = cik.zfill(10)
    try:
        sub = requests.get(_SUB_URL.format(cik10=cik10), headers=_UA, timeout=15).json()
    except Exception:
        logger.exception("EDGAR submissions fetch failed for %s", symbol)
        return None

    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    cutoff = (date.today() - timedelta(days=_LOOKBACK_DAYS)).isoformat()

    jobs = []
    for i, f in enumerate(forms):
        if f != "4" or i >= len(dates) or dates[i] < cutoff:
            continue
        # primaryDocument points at the XSL-styled HTML (xslF345X0n/...); the raw
        # ownership XML is the same filename without that prefix.
        jobs.append((cik, accs[i].replace("-", ""), docs[i].split("/")[-1], dates[i]))
        if len(jobs) >= _MAX_FILINGS:
            break

    if not jobs:
        result = _empty(symbol)
        _SYM_CACHE[symbol] = (now, result)
        return result

    with ThreadPoolExecutor(max_workers=4) as ex:
        parsed = list(ex.map(lambda j: (_parse_form4(j[0], j[1], j[2]), j[3]), jobs))

    buy_val = sell_val = 0.0
    buy_sh = sell_sh = 0
    buyers, sellers = set(), set()
    recent_buys = []
    for p, fdate in parsed:
        if not p:
            continue
        for tx in p["txns"]:
            val = tx["shares"] * tx["price"]
            if tx["code"] == "P":
                buy_val += val
                buy_sh += tx["shares"]
                buyers.add(p["owner"])
                recent_buys.append({"owner": p["owner"], "title": p["title"],
                                    "shares": int(tx["shares"]), "value": int(val),
                                    "date": tx["date"] or fdate})
            else:
                sell_val += val
                sell_sh += tx["shares"]
                sellers.add(p["owner"])

    recent_buys.sort(key=lambda b: b["value"], reverse=True)
    net_val = buy_val - sell_val
    if buyers and len(buyers) >= 2:
        signal = "cluster_buying"
    elif buyers:
        signal = "buying"
    elif sellers and not buyers:
        signal = "selling"
    else:
        signal = "none"

    result = {
        "symbol": symbol,
        "signal": signal,                       # cluster_buying / buying / selling / none
        "buy_value": int(buy_val), "sell_value": int(sell_val), "net_value": int(net_val),
        "buyers": len(buyers), "sellers": len(sellers),
        "lookback_days": _LOOKBACK_DAYS,
        "top_buys": recent_buys[:4],
        "interpretation_points": _interpret(signal, buy_val, sell_val, len(buyers), len(sellers), recent_buys),
    }
    _SYM_CACHE[symbol] = (now, result)
    return result


def _empty(symbol):
    return {"symbol": symbol, "signal": "none", "buy_value": 0, "sell_value": 0,
            "net_value": 0, "buyers": 0, "sellers": 0, "lookback_days": _LOOKBACK_DAYS,
            "top_buys": [], "interpretation_points": [
                {"label": "No open-market activity", "detail":
                 f"No open-market insider purchases or sales filed (Form 4) in the last {_LOOKBACK_DAYS} days. "
                 "Grants, option exercises and tax withholdings are excluded — only conviction trades count here."}]}


def _money(v):
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}k"
    return f"${v:.0f}"


def _interpret(signal, buy_val, sell_val, n_buy, n_sell, buys):
    pts = []
    if signal == "cluster_buying":
        pts.append({"label": "Cluster buying (bullish)", "detail":
            f"{n_buy} different insiders made open-market purchases totalling {_money(buy_val)} — cluster buying "
            "is one of the stronger insider signals; multiple people putting their own cash in agree on upside."})
    elif signal == "buying":
        pts.append({"label": "Insider buying", "detail":
            f"One insider bought {_money(buy_val)} on the open market. A single buyer is encouraging but less "
            "conclusive than a cluster — note the size and the buyer's seniority."})
    elif signal == "selling":
        pts.append({"label": "Selling only", "detail":
            f"{n_sell} insider(s) sold {_money(sell_val)} with no open-market buys. Selling is a weak signal "
            "(diversification, taxes, comp), so don't over-read it — but no one is buying the dip either."})
    else:
        pts.append({"label": "No conviction trades", "detail":
            "No open-market insider buying or selling in the window — neutral."})

    if buys:
        top = buys[0]
        pts.append({"label": "Largest buy", "detail":
            f"{top['title']} {top['owner']} bought {top['shares']:,} shares ({_money(top['value'])}) on {top['date']}."})

    if signal in ("cluster_buying", "buying") and sell_val > buy_val:
        pts.append({"label": "Caveat", "detail":
            f"Insiders also sold {_money(sell_val)} — net flow is actually negative, so the buying is offset."})

    if signal == "cluster_buying":
        bottom = "Net: a genuine leading positive — insiders are voting with their wallets. Confirms a long bias."
    elif signal == "buying":
        bottom = "Net: a mild positive — one insider sees value; corroborate with the setup and the tape."
    elif signal == "selling":
        bottom = "Net: mildly cautionary at most — insider selling rarely predicts much on its own."
    else:
        bottom = "Net: insiders are quiet — not a factor in the thesis either way."
    pts.append({"label": "Bottom line", "detail": bottom})
    return pts
