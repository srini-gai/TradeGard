# TradeGuard

> Personal algorithmic trading assistant for Indian stock markets.
> Scans all 50 Nifty constituent stocks every morning and generates 1-2 high-confidence directional options trade signals (CE/PE) with full entry, stop loss, and 3-tier profit booking ladder.

---

## What it does

- **Morning Screener** — Runs at 9:20 AM IST daily. Scans all 50 Nifty stocks using RSI, EMA, volume, and OI filters. Outputs top 2 CE/PE trade setups ranked by confidence score.
- **Trade Signal Cards** — Each signal shows strike, expiry, entry premium, hard SL, and a T1/T2/T3 profit booking ladder with estimated timelines.
- **Backtesting Engine** — Replays 3 months of historical data, simulates signal generation and trade execution, and reports win rate + P&L summary.
- **Trade Journal** — Log every trade. Track partial bookings at T1/T2/T3. Auto-calculates P&L. Enforces risk rules.
- **TradingView Webhooks** — Receives alerts from your TradingView Pine Script strategies via FastAPI endpoint.
- **Dashboard** — React UI tying everything together — signals, journal, alerts, risk panel, and metrics.

---

## Risk Rules (always enforced)

| Rule | Value |
|------|-------|
| Max trades per day | 2 |
| Max capital risk per trade | 2% |
| Trading cutoff | 2:00 PM IST |
| Stop loss | -40% on premium |
| T1 — book 30% qty at | +38% premium |
| T2 — book 40% qty at | +79% premium |
| T3 — book 30% qty at | +114% premium |
| Contract type | Monthly expiry only |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + Python 3.11+ |
| Frontend | React + TypeScript + Vite + Tailwind |
| Database | SQLite (auto-created, no setup needed) |
| Market Data | yfinance (historical) + Upstox API (live) |
| Scheduler | APScheduler (9:20 AM daily trigger) |
| Alerts | TradingView webhooks → FastAPI |

---

## Project Structure

```
TradeGuard/
├── INITIAL.md                  # Product definition
├── CLAUDE.md                   # Project rules for Claude
├── README.md                   # This file
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point + scheduler
│   │   ├── config.py           # Settings + env vars
│   │   ├── database.py         # SQLite connection + init
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── routers/            # API route handlers
│   │   ├── services/           # Business logic
│   │   └── core/
│   │       ├── screener.py     # Morning screener logic
│   │       ├── backtester.py   # Backtesting engine
│   │       ├── indicators.py   # RSI, EMA, volume calcs
│   │       └── risk.py         # Risk rule constants
│   ├── data/
│   │   ├── nifty50.py          # All 50 symbols
│   │   └── lot_sizes.py        # NSE F&O lot sizes
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── SignalCard.tsx   # Trade signal card with T1/T2/T3 ladder
│       │   ├── Screener.tsx    # Screener results table
│       │   ├── Journal.tsx     # Trade journal
│       │   ├── Backtest.tsx    # Backtest summary
│       │   ├── RiskPanel.tsx   # Risk limits dashboard
│       │   └── Alerts.tsx      # TradingView alerts feed
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── ScreenerPage.tsx
│       │   ├── JournalPage.tsx
│       │   ├── BacktestPage.tsx
│       │   └── AlertsPage.tsx
│       ├── services/           # API call functions
│       ├── hooks/              # Custom React hooks
│       └── types/              # TypeScript interfaces
│
├── database/
│   └── tradeguard.db           # Auto-created on first run
│
├── skills/
│   ├── BACKEND.md
│   ├── FRONTEND.md
│   ├── DATABASE.md             # SQLite patterns
│   ├── DEPLOYMENT.md           # Local run instructions
│   ├── TESTING.md
│   └── TRADING.md              # Screener + backtest logic
│
├── agents/
│   ├── ORCHESTRATOR.md
│   ├── backend-agent.md
│   ├── database-agent.md
│   ├── frontend-agent.md
│   └── screener-agent.md
│
├── .claude/commands/
│   ├── generate-prp.md
│   ├── execute-prp.md
│   └── setup-project.md
│
└── .env                        # API keys — never commit
```

---

## Quick Start

### 1. Clone / setup

```bash
# Copy MicroSaaS template and rename to TradeGuard
# Place all template files as per structure above
```

### 2. Environment variables

```bash
# Create .env in project root
cp .env.example .env

# Fill in your Upstox API credentials
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_ACCESS_TOKEN=your_access_token
VITE_API_URL=http://localhost:8000
```

### 3. Run backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open dashboard

```
http://localhost:5173
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/screener/run` | Run screener now |
| GET | `/api/screener/signals/today` | Today's signals |
| POST | `/api/backtest/run` | Run 3-month backtest |
| GET | `/api/backtest/summary` | Latest backtest results |
| POST | `/api/journal/trades` | Log new trade |
| GET | `/api/journal/trades` | All trades |
| GET | `/api/journal/summary/monthly` | Monthly P&L |
| POST | `/webhook/tradingview` | Receive TV alert |
| GET | `/api/alerts/today` | Today's alerts |

Full API docs at: `http://localhost:8000/docs`

---

## TradingView Webhook Setup

Since the app runs locally, use **ngrok** to expose it to TradingView:

```bash
ngrok http 8000
# Use the generated URL as your TradingView webhook URL:
# https://abc123.ngrok.io/webhook/tradingview
```

TradingView alert message format:
```json
{
  "symbol": "{{ticker}}",
  "action": "BUY_CE",
  "price": {{close}},
  "rsi": 0,
  "timestamp": "{{time}}"
}
```

---

## Build Phases

| Phase | What gets built |
|-------|----------------|
| 1 | Project scaffold + Upstox API + yfinance data fetch |
| 2 | Morning screener — RSI, EMA, volume, OI filters |
| 3 | Backtesting engine — 3 months, T1/T2/T3 simulation |
| 4 | Trade signal cards UI — React with full ladder |
| 5 | Trade journal — SQLite, partial booking, P&L |
| 6 | TradingView webhook receiver |
| 7 | Full dashboard — all panels tied together |

---

## Important Notes

- This is a **personal local tool** — no authentication, no deployment, no cloud needed
- Options premiums in backtesting are **approximated** using Black-Scholes (real historical options data requires paid subscriptions)
- Backtest results are **directional validation** — not a guarantee of future performance
- Always apply your own judgment before executing any trade signal
- **No trading system guarantees profits** — risk management is the foundation

---

## Upstox API Setup

1. Log in to [Upstox Developer Portal](https://developer.upstox.com)
2. Create a new app
3. Get your `API Key` and `API Secret`
4. Generate an `Access Token`
5. Add all three to your `.env` file

---

*Built with FastAPI + React + SQLite + yfinance + Upstox API*
*For personal use only — not financial advice*
