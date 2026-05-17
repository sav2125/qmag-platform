# Qullamaggie Platform

A full-stack trading scanner that identifies Kristjan Qullamaggie's four primary setups across the full US equity universe and delivers a daily email digest with actionable entry, stop, and target levels.

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

Each result shows: **Entry · Stop · T1 · T2 · R:R · RS score · Grade · Risk%**

---

## Features

### Scanner
- **8 stock universes** — Full S&P 500 (503 stocks, live), Nasdaq 100, Large Cap (S&P 500 + Nasdaq), Mid Cap (S&P 400, 369 stocks), Small Cap (Alpaca universe minus large/mid), All US Equities (~7,000), Tech Leaders (30), My Watchlist
- **Advanced filters** — Min RS, Min ADR%, Min daily % change, Above EMA21/50, Max Base Length (TB only, up to 5 years), Top N results
- **State classification** — 🚀 Breakout (enter now), ⏳ In Base (set alert), 📈 Active (enter near market)
- **Action hints** — Context-aware "Enter now / Enter near mkt / Alert +X% away" per state
- **Risk%** — Displays `(entry − stop) / entry` for instant position sizing
- **Grade** — A/B/C composite score across volume, RS, base quality, and R:R
- **State legend** — Hover tooltips on each state badge; legend footer below the table

### Data
- **Primary source:** [Alpaca Markets](https://alpaca.markets) free paper trading API — works on cloud hosts (200 req/min)
- **Rate limiting:** `threading.Semaphore(4)` + exponential backoff with full jitter + 429 Retry-After handling + 4 retries
- **S&P 500 constituents:** Fetched from [datasets/s-and-p-500-companies](https://github.com/datasets/s-and-p-500-companies) GitHub CSV, cached 24 hours, falls back to hardcoded 100-stock sample
- **All US universe:** Alpaca `/v2/assets` endpoint, cached 24 hours; falls back to 1,000+ curated static list

### Frontend
- **Dashboard** — Scan controls, advanced filter panel, stats bar (Total / Grade A / EPs), results table
- **Setup pages** — Deep-dive educational pages for EP, TB, PP, and PULL with ASCII charts, criteria, and entry/stop rules
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

> ⚠ Scanning "All US Equities" (~7,000 stocks) takes 15–30 minutes. Use a focused universe for daily scans.

---

## Scan Filters

| Filter | Description |
|--------|-------------|
| **Universe** | Which stock list to scan |
| **Setup Filter** | EP / TB / PP / PULL — leave blank for all |
| **Min RS** | Minimum Relative Strength score vs SPY (0–100) |
| **Top N** | Return only the top N results sorted by grade × RS |
| **Min ADR%** | Average Daily Range % — filters out low-volatility stocks |
| **Min Day Chg%** | Minimum today's % change (e.g. ≥5% for EP catalyst filter) |
| **Price > EMA21** | Require price above 21-day exponential MA |
| **Price > EMA50** | Require price above 50-day exponential MA |
| **Max Base Length** | TB only — maximum base duration (3 months → 5 years) |

---

## Email Digest

### Manual send

```bash
cd backend
python daily_digest.py                              # S&P 500, top 20
python daily_digest.py --universe nasdaq100         # Nasdaq 100 only
python daily_digest.py --setup ep --min-rs 70       # EP setups, RS ≥ 70
python daily_digest.py --universe all --top 30      # All US, top 30
```

### Automated daily routine

A scheduled routine runs every weekday at **7:00 AM ET** via the Claude Code `/schedule` skill. It scans the S&P 500 (top 20, min RS 50) and emails the digest automatically.

To reconfigure the schedule, run `/schedule` in Claude Code and update the existing routine.

---

## RS Score

IBD-style Relative Strength score (0–100) versus SPY:

```
RS = 40% × (3m perf ratio) + 20% × (6m) + 20% × (9m) + 20% × (12m)
     mapped to 0–100 (50 = matches SPY, 100 = maximum outperformance)
```

| Score | Label |
|-------|-------|
| ≥ 90 | RS Elite |
| ≥ 75 | RS Strong |
| ≥ 50 | RS Average |
| ≥ 25 | RS Weak |
| < 25 | RS Laggard |

Use `min_rs=70` (or the slider) to filter to stocks clearly outperforming the market.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + current date |
| `GET` | `/scan` | Run scanner, returns setup list |
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
| `setup` | string | null | ep, tb, pp, pull |
| `min_rs` | float | 50 | Minimum RS score (0–100) |
| `min_score` | float | 0 | Minimum confidence score (0–100) |
| `top` | int | 20 | Max results returned (1–100) |
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
│   │   ├── patterns.py          EP, TB (configurable length), PP, PULL detectors
│   │   ├── rs_rank.py           IBD-style RS score vs SPY
│   │   └── engine.py            Scan orchestration, ADR/EMA/RS filters, grading
│   └── notifier/
│       └── email_sender.py      HTML email digest builder + SMTP sender
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx          Dashboard — scan controls + results table
        │   ├── setups/           Educational pages for EP, TB, PP, PULL
        │   │   ├── page.tsx      Setup overview hub
        │   │   ├── ep/page.tsx   Episodic Pivot deep dive
        │   │   ├── tb/page.tsx   Tight Base deep dive
        │   │   ├── pp/page.tsx   Pocket Pivot deep dive
        │   │   └── pull/page.tsx EMA Pullback deep dive
        │   ├── watchlist/        Watchlist manager UI
        │   └── settings/         Email test + manual digest trigger
        ├── components/
        │   ├── SetupBadge.tsx    EP/TB/PP/PULL colored badges + R:R + Grade badges
        │   └── SetupTable.tsx    Results table: state badges, action hints, risk%
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
