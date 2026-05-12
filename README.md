# Qullamaggie Platform

A full-stack web app that scans for Kristjan Qullamaggie's four primary trading setups and delivers a daily email digest with actionable entry, stop, and target levels.

## Setups

| Badge | Name | Signal |
|-------|------|--------|
| **EP** | Episodic Pivot | Catalyst gap/surge ≥5% on ≥2× avg volume, stock was basing; tight consolidation follows; entry on breakout above EP high |
| **TB** | Tight Base | Flat base ≤8% range, resistance retested ≥2×, volume breakout |
| **PP** | Pocket Pivot | Up-day volume exceeds the highest down-day volume in the prior 10 days, above 10-day MA with 10 EMA > 20 EMA |
| **PULL** | EMA Pullback | Stage 2 uptrend (EMA21 > EMA50, rising), price touched EMA21 in last 1–5 bars, RSI 38–68 |

Each result shows: **Entry · Stop · T1 · T2 · R:R · RS score · Grade**

---

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # fill in your email credentials
python main.py                # starts FastAPI on http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                   # starts Next.js on http://localhost:3000
```

Then open **http://localhost:3000**, hit **Run Scan**, and the dashboard fills with today's setups.

---

## Email Notifications

### Configure SMTP

Edit `backend/.env`:

```env
NOTIFY_TO_EMAIL=you@example.com
NOTIFY_FROM_EMAIL=yourapp@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourapp@gmail.com
SMTP_PASSWORD=your-gmail-app-password
```

For Gmail, generate an **App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2FA).

### Send a digest manually

```bash
cd backend
python daily_digest.py                         # scan sp500, email top 20
python daily_digest.py --universe tech         # tech-only scan
python daily_digest.py --setup ep --min-rs 70  # EP setups, elite RS only
```

### Daily routine (automated)

The scheduled routine runs every weekday at **7:00 AM ET** via the Claude Code schedule skill. It scans the S&P 500 and emails the top 20 setups.

To re-configure the schedule, run `/schedule` in Claude Code.

---

## Project Structure

```
qmag-platform/
├── backend/
│   ├── main.py               FastAPI server (port 8000)
│   ├── daily_digest.py       Standalone daily digest runner
│   ├── requirements.txt
│   ├── .env.example
│   ├── scanner/
│   │   ├── fetcher.py        yfinance OHLCV fetcher + in-memory cache
│   │   ├── patterns.py       EP, TB, PP, PULL detectors
│   │   ├── rs_rank.py        IBD-style RS score vs SPY
│   │   └── engine.py         Scanning orchestration + RS filter
│   └── notifier/
│       └── email_sender.py   HTML email digest builder + SMTP sender
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx       Dashboard (scan controls + results table)
        │   ├── watchlist/     Watchlist manager
        │   └── settings/      Email test + manual digest trigger
        ├── components/
        │   ├── SetupBadge.tsx EP/TB/PP/PULL colored badges
        │   └── SetupTable.tsx Results table with entry/stop/targets
        └── lib/
            └── api.ts         API client
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/scan` | Run Qullamaggie scan |
| `GET` | `/watchlist` | Get watchlist symbols |
| `POST` | `/watchlist` | Add symbol |
| `DELETE` | `/watchlist/{symbol}` | Remove symbol |
| `POST` | `/notify/test` | Send test email with mock data |
| `POST` | `/notify/send` | Scan + send live digest |

**Scan query params:** `universe`, `setup` (ep/tb/pp/pull), `min_rs` (0–100), `min_score`, `top`

---

## RS Score

Each setup includes an IBD-style Relative Strength score (0–100) versus SPY:

```
RS = 40% × (3m ratio) + 20% × (6m) + 20% × (9m) + 20% × (12m)
     mapped to 0-100  (50 = matches SPY, 100 = maximum outperformance)
```

| Score | Label |
|-------|-------|
| ≥ 90 | RS Elite |
| ≥ 75 | RS Strong |
| ≥ 50 | RS Average |
| ≥ 25 | RS Weak |
| < 25 | RS Laggard |

Use `--min-rs 70` (or the slider in the dashboard) to filter to stocks clearly outperforming the market.

---

> Not financial advice. Always confirm setups on your own chart before trading.
