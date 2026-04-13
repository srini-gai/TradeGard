# INITIAL.md - TradeGuard

> Fill this out, then run `/generate-prp INITIAL.md`

---

## PRODUCT

**Name:** TradeGuard

**Description:** A personal algorithmic trading assistant for Indian stock markets. Scans all 50 Nifty constituent stocks every morning, generates 1-2 high-confidence directional options trade signals (CE/PE) with entry, stop loss, and a 3-tier profit booking ladder (T1/T2/T3). Includes a backtesting engine (3 months historical), trade journal, TradingView webhook receiver, and a full React dashboard. Built for personal use — no auth, no payments, runs locally.

**Type:** Local Tool (Personal Use)

---

## TECH STACK

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + Python 3.11+ |
| Frontend | React + TypeScript + Vite |
| Database | SQLite + SQLAlchemy |
| Market Data | yfinance (free, 3 months historical) |
| Broker API | Upstox API (live options chain) |
| Scheduler | APScheduler (9:20 AM daily screener) |
| Alerts | TradingView Webhooks → FastAPI |
| UI | Tailwind CSS |
| Auth | None (local personal tool) |
| Payments | None |
| Deployment | Local only (uvicorn + vite dev) |

---

## MODULES

### Module 1: Data Fetcher

**Description:** Fetches historical OHLCV data for all 50 Nifty stocks using yfinance. Connects to Upstox API for live options chain data (premiums, OI, IV).

**Models:**
```
StockData:
  - symbol: str
  - date: date
  - open, high, low, close, volume: float
  - fetched_at: datetime
```

**Endpoints:**
```
GET  /api/data/historical/{symbol}   - Get 3 months OHLCV
GET  /api/data/options/{symbol}      - Get live options chain
GET  /api/data/nifty50              - List all 50 symbols
POST /api/data/refresh              - Force refresh all data
```

---

### Module 2: Morning Screener

**Description:** Runs at 9:20 AM daily. Scans all 50 Nifty stocks using RSI, EMA, volume, and OI filters. Outputs top 2 CE/PE trade signals with strike, expiry, premium, and a confidence score.

**Screener Logic:**
```
Step 1 - Trend Filter:
  → Stock above 20 EMA → bullish (CE candidate)
  → Stock below 20 EMA → bearish (PE candidate)

Step 2 - Momentum Filter:
  → RSI 55-70 → bullish confirmation
  → RSI 30-45 → bearish confirmation

Step 3 - Volume Filter:
  → Today volume > 1.5x 10-day average

Step 4 - OI Filter:
  → OI buildup at ATM/OTM strike
  → IV within acceptable range (not overpriced)

Step 5 - Score & Rank:
  → Score 0-100 based on filter strength
  → Output top 2 stocks with full trade details
```

**Models:**
```
Signal:
  - id, symbol: str
  - signal_date: date
  - direction: str (CE/PE)
  - strike: float
  - expiry: date
  - entry_premium: float
  - sl_premium: float
  - t1_premium, t2_premium, t3_premium: float
  - t1_date, t2_date, t3_date: date (estimated)
  - confidence_score: int (0-100)
  - rationale: JSON (list of reasons)
  - created_at: datetime
```

**Endpoints:**
```
GET  /api/screener/run           - Run screener now
GET  /api/screener/signals/today - Get today's signals
GET  /api/screener/signals       - Get all past signals
GET  /api/screener/signals/{id}  - Get one signal
```

---

### Module 3: Backtesting Engine

**Description:** Replays 3 months of historical data. For each trading day, runs the screener logic and simulates trade execution — checking if SL, T1, T2, T3 were hit on subsequent days. Outputs win rate, average P&L, and monthly breakdown.

**Backtest Logic:**
```
For each day in last 3 months:
  → Run screener on that day's OHLCV
  → If signal: simulate entry at open premium
  → Check next N days:
      premium drops 40% → SL hit → full loss
      premium rises 38% → T1 hit → book 30%, move SL to entry
      premium rises 79% → T2 hit → book 40%, trail SL
      premium rises 114% → T3 hit → book 30%, trade complete
  → Record outcome

Output:
  → Total signals, win rate %, average P&L per trade
  → Best trade, worst trade, max drawdown
  → Monthly breakdown table
```

**Note:** Options premiums approximated using Black-Scholes since historical options chain data is not freely available.

**Models:**
```
BacktestRun:
  - id, run_date: datetime
  - period_start, period_end: date
  - total_signals: int
  - win_rate: float
  - avg_pnl: float
  - best_trade_pnl, worst_trade_pnl: float
  - max_drawdown: float
  - results_json: JSON

BacktestTrade:
  - id, backtest_run_id: FK
  - symbol, direction: str
  - entry_date, exit_date: date
  - entry_premium, exit_premium: float
  - outcome: str (T1/T2/T3/SL/EXPIRED)
  - pnl: float
  - pnl_pct: float
```

**Endpoints:**
```
POST /api/backtest/run           - Run backtest (async)
GET  /api/backtest/results       - Get all backtest runs
GET  /api/backtest/results/{id}  - Get one run with trades
GET  /api/backtest/summary       - Latest run summary
```

---

### Module 4: Trade Journal

**Description:** Logs every trade taken. Tracks entry, partial exits at T1/T2, and full exit at T3 or SL. Auto-calculates P&L per booking. Monthly and weekly summary.

**Trading Rules (enforced):**
- Max 2 trades per day — hard limit
- Max 2% capital risk per trade
- Mandatory stop loss — cannot log a trade without SL
- No new trades after 2:00 PM IST
- Monthly expiry contracts only

**Models:**
```
Trade:
  - id, signal_id: FK (optional)
  - symbol, direction: str (CE/PE)
  - strike: float
  - expiry: date
  - entry_date, entry_time: datetime
  - entry_premium: float
  - lots: int
  - lot_size: int
  - sl_premium: float
  - t1_premium, t2_premium, t3_premium: float
  - status: str (OPEN/PARTIAL/CLOSED/SL_HIT)
  - t1_booked_at, t2_booked_at, t3_booked_at: datetime (nullable)
  - exit_premium: float (nullable)
  - total_pnl: float (nullable)
  - notes: str
  - created_at: datetime

PartialBooking:
  - id, trade_id: FK
  - level: str (T1/T2/T3/SL)
  - booked_at: datetime
  - qty_booked: int
  - exit_premium: float
  - pnl: float
```

**Endpoints:**
```
POST /api/journal/trades          - Log new trade
GET  /api/journal/trades          - List all trades
GET  /api/journal/trades/today    - Today's trades
GET  /api/journal/trades/{id}     - Get one trade
PUT  /api/journal/trades/{id}     - Update trade (book partial/full)
GET  /api/journal/summary/weekly  - Weekly P&L summary
GET  /api/journal/summary/monthly - Monthly P&L summary
```

---

### Module 5: TradingView Webhook Receiver

**Description:** FastAPI endpoint that receives webhook alerts from TradingView Pine Script. Logs signal with timestamp and optionally creates a journal entry.

**Endpoints:**
```
POST /webhook/tradingview         - Receive TV alert
GET  /api/alerts                  - List all received alerts
GET  /api/alerts/today            - Today's alerts
```

**Webhook Payload (from TradingView):**
```json
{
  "symbol": "RELIANCE",
  "action": "BUY_CE",
  "price": 2961.5,
  "rsi": 62,
  "timestamp": "2026-04-06T09:21:00"
}
```

---

### Module 6: Dashboard (React)

**Pages:**
```
/                    - Main dashboard (signals + metrics)
/screener            - Morning screener results + run button
/backtest            - Run backtest + view summary results
/journal             - Trade journal table + P&L summary
/alerts              - TradingView alerts feed
```

**Components:**
```
SignalCard           - Full trade card with ladder (T1/T2/T3)
ScreenerTable        - Ranked list of today's setups
BacktestSummary      - Win rate, avg P&L, monthly breakdown
JournalTable         - All trades with status + P&L
RiskPanel            - Daily limits, capital at risk, window
AlertsFeed           - Live TradingView alerts
MetricsBar           - Today P&L, week P&L, trades used
```

---

## RISK RULES (HARDCODED — NEVER BYPASS)

```python
MAX_TRADES_PER_DAY = 2
MAX_CAPITAL_RISK_PCT = 0.02      # 2% per trade
TRADING_CUTOFF_HOUR = 14         # No trades after 2 PM IST
PROFIT_BOOKING_T1_PCT = 0.38     # Book 30% qty at +38%
PROFIT_BOOKING_T2_PCT = 0.79     # Book 40% qty at +79%
PROFIT_BOOKING_T3_PCT = 1.14     # Book 30% qty at +114%
QTY_T1 = 0.30
QTY_T2 = 0.40
QTY_T3 = 0.30
SL_PCT = 0.40                    # Exit 100% at -40% premium
```

---

## NIFTY 50 SYMBOLS (yfinance format)

```python
NIFTY50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "BAJFINANCE.NS", "WIPRO.NS", "HCLTECH.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
    "TECHM.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "POWERGRID.NS", "NTPC.NS",
    "ONGC.NS", "COALINDIA.NS", "ADANIPORTS.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS", "DRREDDY.NS", "CIPLA.NS",
    "DIVISLAB.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "BRITANNIA.NS",
    "INDUSINDBK.NS", "GRASIM.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "BPCL.NS",
    "LTIM.NS", "HINDALCO.NS", "VEDL.NS", "SHRIRAMFIN.NS", "ADANIENT.NS"
]
```

---

## MVP SCOPE

Must Have:
- [x] Morning screener (RSI + EMA + Volume + OI)
- [x] Top 2 signals with full T1/T2/T3 ladder
- [x] Backtesting engine (3 months, Black-Scholes approx)
- [x] Trade journal with partial booking tracker
- [x] TradingView webhook receiver
- [x] React dashboard with all panels
- [x] Risk rules enforced (2 trades/day, 2% risk, 2 PM cutoff)

Nice to Have:
- [ ] Telegram alert on signal generation
- [ ] Email summary at end of day
- [ ] CSV export of journal
- [ ] Options chain live view

---

## ACCEPTANCE CRITERIA

- [ ] Screener runs at 9:20 AM and outputs exactly 2 signals
- [ ] Each signal shows: symbol, CE/PE, strike, expiry, entry, SL, T1, T2, T3, timeline
- [ ] Backtest runs on 3 months data and returns win rate + avg P&L
- [ ] Journal enforces max 2 trades/day hard limit
- [ ] Journal enforces no new entries after 2 PM
- [ ] TradingView webhook receives and logs alerts correctly
- [ ] Dashboard loads all panels without errors
- [ ] SQLite DB auto-created on first run

---

## RUN

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install
npm run dev

# Run screener manually
curl -X POST http://localhost:8000/api/screener/run

# Run backtest
curl -X POST http://localhost:8000/api/backtest/run
```
