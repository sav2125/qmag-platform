# Qullamaggie Platform

A full-stack trading scanner that identifies Kristjan Qullamaggie's trading setups across the full US equity universe and delivers a daily email digest with actionable entry, stop, and target levels.

**Live demo:** [https://qmag-platform-1.onrender.com](https://qmag-platform-1.onrender.com)  
**Backend API:** [https://qmag-platform.onrender.com](https://qmag-platform.onrender.com)

---

## Setups

| Badge | Name | Signal |
|-------|------|--------|
| **EP** | Episodic Pivot | Catalyst gap/surge ≥5% on ≥2× avg volume; tight consolidation follows; entry on breakout above EP high |
| **TB** | Tight Base | Flat base ≤8–10% range, resistance retested ≥2×, volume breakout; base can be 2 weeks to 5 years |
| **PP** | Pocket Pivot | Up-day volume exceeds the highest down-day volume in the prior 10 days, above 10-day MA, EMA21 > EMA50 |
| **PULL** | EMA Pullback | Stage 2 uptrend (EMA21 > EMA50, rising), price touched EMA21 in last 1–5 bars, RSI 38–68 |
| **FBD** | Failed Breakdown | Price breaks below support 0.4–6%, snaps back above within 1–3 bars; trapped shorts fuel the reversal |
| **WYS** | Wyckoff Spring | Shakeout ≤3% below a tight accumulation range (15% range, 40 bars), snap-back within 3 bars; highest-conviction bear trap |

Each result shows: **Entry · Stop · T1 · T2 · R:R · RS · Grade · Risk% · Weinstein Stage · A/D Net**

---

## Features

### Scanner
- **8 stock universes** — Full S&P 500 (503 stocks, live), Nasdaq 100, Large Cap (S&P 500 + Nasdaq), Mid Cap (S&P 400, 369 stocks), Small Cap (Alpaca universe minus large/mid), All US Equities (~7,000), Tech Leaders (30), My Watchlist
- **6 setup types** — EP, TB, PP, PULL, FBD (Failed Breakdown / bear trap), WYS (Wyckoff Spring)
- **Advanced filters** — Min RS, Min ADR%, Min daily % change, Above EMA21/50, Max Base Length (TB only, up to 5 years), Top N results
- **State classification** — Breakout (enter now), In Base (set alert), Active (enter near market)
- **Action hints** — Context-aware "Enter now / Enter near mkt / Alert at $X.XX (+X%)" per state
- **Risk%** — Displays `(entry - stop) / entry` for instant position sizing
- **Weinstein Stage** — S1/S2/S3/S4 badge per result using the 30-week (150-bar) MA; only Stage 2 is tradeable
- **A/D Net** — O'Neill accumulation/distribution day count over the last 25 bars; positive = institutional buying
- **Overextension penalty** — RSI > 80 or price > 8% above EMA21 docks the confidence score; shown in notes column
- **Bull exhaustion warning** — RSI > 70 + volume fading + price > 3% above EMA21 → "Bull exhaustion" flag in Notes column
- **RVOL** — Relative Volume: today's volume vs 20-day avg; shown under Price column (violet when ≥2×)
- **ICS** — Institutional Composite Score (OBV + CMF + A/D line + MFI → 0–100); shown under A/D column
- **Quality score** — Grade uses `confidence x stop_factor x rr_factor`; tight stops + good R:R rank higher than sloppy setups
- **State legend** — Hover tooltips on every badge; footer legend below the table

### Data
- **Primary source:** [Alpaca Markets](https://alpaca.markets) free paper trading API — works on cloud hosts (200 req/min)
- **Rate limiting:** `threading.Semaphore(4)` + exponential backoff with full jitter + 429 Retry-After handling + 4 retries
- **S&P 500 constituents:** Fetched from [datasets/s-and-p-500-companies](https://github.com/datasets/s-and-p-500-companies) GitHub CSV, cached 24 hours, falls back to hardcoded 100-stock sample
- **All US universe:** Alpaca `/v2/assets` endpoint, cached 24 hours; falls back to 1,000+ curated static list

### Frontend
- **Analyze page** — Deep-dive for any individual stock: all 6 setups, RSI/MACD/ADX, MA stack, Weinstein stage, ICS, A/D Net, 9-item signal checklist, early warnings, and score breakdown
- **Dashboard** — Scan controls, advanced filter panel, stats bar (Total / Grade A / EPs), full results table
- **Setup pages** — Deep-dive educational pages for EP, TB, PP, PULL, and FBD with ASCII charts, criteria, comparison tables, and entry/stop rules
- **Scanner signals guide** — Plain-English explanation of Weinstein Stage, A/D Net, Quality Score, and Overextension Penalty on the Setups hub page
- **Scoring page** — Full algorithm reasoning: every formula, every weight, every threshold, and the WHY behind each design decision
- **Watchlist** — Persistent per-symbol list scanned separately
- **Email settings** — Test SMTP config and trigger manual digests from the UI
- **Light mode forced** — Consistent UI regardless of OS dark mode preference

---

## Quick Start

### 1. Get Alpaca API keys (free)

Sign up for a **paper trading** account at [alpaca.markets](https://alpaca.markets) — no credit card required. Copy your API Key ID and Secret from the dashboard.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env: fill in ALPACA_API_KEY, ALPACA_API_SECRET, and email settings
python main.py                # FastAPI on http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                   # Next.js on http://localhost:3000
```

Open **http://localhost:3000**, choose a universe, set your filters, and press **Run Scan**.

---

## Environment Variables

```env
# backend/.env

# Alpaca Markets — free paper trading account at alpaca.markets
ALPACA_API_KEY=your-alpaca-key-id
ALPACA_API_SECRET=your-alpaca-secret-key

# Email notifications
NOTIFY_TO_EMAIL=you@example.com
NOTIFY_FROM_EMAIL=yourapp@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourapp@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# CORS — add your deployed frontend URL here
ALLOWED_ORIGINS=https://your-app.onrender.com
```

For Gmail, generate an **App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2FA enabled).

---

## Stock Universes

| Universe | Count | Source |
|----------|-------|--------|
| S&P 500 | ~503 | GitHub CSV, refreshed every 24 h |
| Nasdaq 100 | 100 | Hardcoded (QQQ components) |
| Large Cap | ~522 | S&P 500 + Nasdaq 100 combined |
| Mid Cap | 369 | S&P 400 constituents (hardcoded) |
| Small Cap | varies | Alpaca live universe minus large/mid |
| All US Equities | ~7,000 | Alpaca `/v2/assets`, cached 24 h |
| Tech Leaders | 30 | Nasdaq 100 tech subset |
| My Watchlist | user-defined | Persistent JSON file |

> Scanning "All US Equities" (~7,000 stocks) takes 15-30 minutes. Use a focused universe for daily scans.

---

## Scan Filters

| Filter | Description |
|--------|-------------|
| **Universe** | Which stock list to scan |
| **Setup Filter** | EP / TB / PP / PULL / FBD — leave blank for all |
| **Min RS** | Minimum Relative Strength score vs SPY (0-100) |
| **Top N** | Return only the top N results sorted by quality score x RS |
| **Min ADR%** | Average Daily Range % — filters out low-volatility stocks |
| **Min Day Chg%** | Minimum today's % change (e.g. >=5% for EP catalyst filter) |
| **Price > EMA21** | Require price above 21-day exponential MA |
| **Price > EMA50** | Require price above 50-day exponential MA |
| **Max Base Length** | TB only — maximum base duration (3 months to 5 years) |

---

## Scanner Signal Reference

These signals appear in every scan result and help filter the highest-quality setups.

### Weinstein Stage (Stg column)

Classifies each stock into one of Stan Weinstein's four stages using the 30-week (150-bar) moving average:

| Badge | Stage | Condition | Action |
|-------|-------|-----------|--------|
| S1 | Basing | Flat MA, price at/below MA | Wait |
| S2 | Advancing | Rising MA, price above MA | **Trade here** |
| S3 | Topping | MA rolling over after advance | Avoid new longs |
| S4 | Declining | Falling MA, price below MA | Short only |

### A/D Net (A/D column)

O'Neill-style institutional accumulation/distribution count over the last 25 bars:
- **Accumulation day:** close up >=0.2% vs prior, volume > prior bar, close in upper 50% of the day's range
- **Distribution day:** close down >=0.2% vs prior, volume > prior bar
- **Net = acc days - dist days.** Positive = institutions buying. Negative = distributing.

### Overextension Penalty

When RSI > 80 or price is >8% above EMA21, a penalty is applied to the confidence score:
- RSI penalty: `(RSI - 80) x 0.5 pts` per RSI point above 80
- EMA21 extension penalty: up to 10 pts when price > 8% above EMA21
- Maximum total penalty: 20 pts. Shown as "Overextended (-Xpts)" in the notes column.

### Quality Score and Grade

Grade is based on a unified composite score that incorporates all signals — not just raw pattern confidence. Full algorithm reasoning is on the **[/scoring page](https://qmag-platform-1.onrender.com/scoring)** of the live site.

```
# Step 1 — quality score (adjusts confidence for stop width and R:R)
stop_factor   = clip(1 - stop_pct / 0.15, 0.40, 1.00)   # wide stop → lower score
rr_factor     = clip(rr / 2.0, 0.50, 1.20)               # poor R:R → lower; great R:R → +20% bonus
quality_score = min(1.0, confidence x stop_factor x rr_factor)

# Step 2 — composite score (0-100)
base     = quality_score x 60    # pattern quality:  0-60 pts  (60% weight)
rs_pts   = rs_score x 0.25       # relative strength: 0-25 pts  (25% weight)
stg_pts  = {S2:10, S1:4, S3:2, S4:0, unknown:5}   # Weinstein: 0-10 pts (10% weight)
ad_pts   = clamp(ad_net x 0.5, -5, +5)             # O'Neill A/D: ±5 pts  (5% weight)

composite = base + rs_pts + stg_pts + ad_pts

# Step 3 — grade thresholds (calibrated to real detector confidence ranges)
A: composite >= 72    B: >= 58    C: >= 44    D: < 44
```

**Why these weights?** Pattern quality is the primary signal (60%). RS is the most important market-context filter Qullamaggie uses (25%). Stage 2 is a required condition, not optional (10%). A/D is a tiebreaker only (5%).

**Why these grade thresholds?** Originally A≥80, B≥65, C≥50 — but detector confidence outputs realistically range 0.60–0.90, not 0.90–1.00. A textbook-perfect EP with RS 90 + Stage 2 + accumulation scored 74.9 — which should be an A. Thresholds were recalibrated accordingly.

A great pattern with weak RS or non-Stage-2 **cannot** grade A — intentional. Qullamaggie only trades Stage 2 leaders with strong RS.

---

## Email Digest

### Manual send

```bash
cd backend
python daily_digest.py                              # S&P 500, top 20
python daily_digest.py --universe nasdaq100         # Nasdaq 100 only
python daily_digest.py --setup ep --min-rs 70       # EP setups, RS >= 70
python daily_digest.py --universe all --top 30      # All US, top 30
```

### Automated daily routine

A scheduled routine runs every weekday at **7:00 AM ET** via the Claude Code `/schedule` skill. It scans the S&P 500 (top 20, min RS 50) and emails the digest automatically.

To reconfigure the schedule, run `/schedule` in Claude Code and update the existing routine.

---

## RS Score

IBD-style Relative Strength score (0-100) versus SPY:

```
RS = 40% x (3m perf ratio) + 20% x (6m) + 20% x (9m) + 20% x (12m)
     mapped to 0-100 (50 = matches SPY, 100 = maximum outperformance)
```

| Score | Label |
|-------|-------|
| >= 90 | RS Elite |
| >= 75 | RS Strong |
| >= 50 | RS Average |
| >= 25 | RS Weak |
| < 25 | RS Laggard |

Use `min_rs=70` (or the slider) to filter to stocks clearly outperforming the market.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + current date |
| `GET` | `/scan` | Run scanner, returns setup list |
| `GET` | `/analyze/{symbol}` | Full single-stock analysis: all 6 setups, RSI/MACD/ADX, checklist, warnings, score breakdown |
| `GET` | `/debug/fetch` | Test Alpaca data fetch for a single symbol |
| `GET` | `/watchlist` | Get saved watchlist symbols |
| `POST` | `/watchlist` | Add symbol to watchlist |
| `DELETE` | `/watchlist/{symbol}` | Remove symbol |
| `POST` | `/notify/send` | Run scan + email live digest |
| `POST` | `/notify/test` | Email test digest with mock data |

### `/scan` query parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `universe` | string | `sp500` | sp500, nasdaq100, largecap, midcap, smallcap, all, tech, watchlist |
| `setup` | string | null | ep, tb, pp, pull, fbd, wys |
| `min_rs` | float | 50 | Minimum RS score (0-100) |
| `min_score` | float | 0 | Minimum confidence score (0-100) |
| `top` | int | 20 | Max results returned (1-100) |
| `min_adr` | float | 0 | Min Average Daily Range % |
| `min_pct_change` | float | 0 | Min today's % change |
| `above_ema21` | bool | false | Require price > EMA21 |
| `above_ema50` | bool | false | Require price > EMA50 |
| `max_base_bars` | int | 500 | Max TB base length in bars (~5 bars/week) |

---

## Project Structure

```
qmag-platform/
├── backend/
│   ├── main.py                  FastAPI server (port 8000)
│   ├── daily_digest.py          Standalone daily digest runner (CLI)
│   ├── requirements.txt
│   ├── .env.example
│   ├── .python-version          Pins Python 3.12 for Render
│   ├── scanner/
│   │   ├── fetcher.py           Alpaca OHLCV fetcher, universe lists, rate limiting
│   │   ├── patterns.py          EP, TB, PP, PULL, FBD detectors + enrichment helpers
│   │   ├── rs_rank.py           IBD-style RS score vs SPY
│   │   └── engine.py            Scan orchestration, filters, enrichment, quality grading
│   └── notifier/
│       └── email_sender.py      HTML email digest builder + SMTP sender
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx          Dashboard — scan controls + results table
        │   ├── setups/           Educational setup pages
        │   │   ├── page.tsx      Hub: all setups + scanner signals guide
        │   │   ├── ep/page.tsx   Episodic Pivot deep dive
        │   │   ├── tb/page.tsx   Tight Base deep dive
        │   │   ├── pp/page.tsx   Pocket Pivot deep dive
        │   │   ├── pull/page.tsx EMA Pullback deep dive
        │   │   └── fbd/page.tsx  Failed Breakdown deep dive
        │   ├── analyze/          Single-stock deep-dive page
        │   ├── scoring/          Scoring algorithm deep-dive (all formulas + rationale)
        │   ├── watchlist/        Watchlist manager UI
        │   └── settings/         Email test + manual digest trigger
        ├── components/
        │   ├── SetupBadge.tsx    Setup, Grade, R:R, Stage, and A/D Net badges
        │   └── SetupTable.tsx    Results table: state badges, action hints, risk%, stage, A/D
        └── lib/
            └── api.ts            Typed API client (auto-detects prod vs local URL)
```

---

## Deployment (Render)

Both services are on Render's free tier.

### Backend — Web Service
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Python version:** 3.12 (pinned via `.python-version`)
- **Environment variables:** Set `ALPACA_API_KEY`, `ALPACA_API_SECRET`, email vars, and `ALLOWED_ORIGINS` in the Render dashboard

### Frontend — Static Site
- **Build command:** `npm install && npm run build`
- **Publish directory:** `out`
- **Environment variable:** `NEXT_PUBLIC_API_URL=https://qmag-platform.onrender.com`

> Free tier services spin down after 15 minutes of inactivity. The first scan after a cold start may take ~30 seconds while the backend wakes up.

---

> **Not financial advice.** Entry, stop, and target levels are algorithmically computed. Always confirm setups on your own chart before trading.
