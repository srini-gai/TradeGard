# CLAUDE.md - TradeGuard Project Rules

> Rules Claude follows in every conversation in this project.

---

## Tech Stack

- **Backend:** FastAPI + Python 3.11+
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Database:** SQLite + SQLAlchemy (no migrations needed — auto-create on startup)
- **Market Data:** yfinance (historical) + Upstox API (live options chain)
- **Scheduler:** APScheduler (9:20 AM daily screener trigger)
- **Auth:** None — local personal tool
- **Payments:** None

---

## Project Structure

```
TradeGuard/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + scheduler setup
│   │   ├── config.py         # Settings + env vars
│   │   ├── database.py       # SQLite connection
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── routers/          # API route handlers
│   │   ├── services/         # Business logic
│   │   └── core/
│   │       ├── screener.py   # Screener logic
│   │       ├── backtester.py # Backtest engine
│   │       ├── indicators.py # RSI, EMA, volume calcs
│   │       └── risk.py       # Risk rule enforcement
│   ├── data/
│   │   └── nifty50.py        # All 50 symbols list
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # Reusable UI components
│       ├── pages/            # Page-level components
│       ├── hooks/            # Custom React hooks
│       ├── services/         # API call functions
│       └── types/            # TypeScript interfaces
├── database/
│   └── tradeguard.db         # Auto-created SQLite file
├── skills/
├── agents/
├── .claude/commands/
├── .env
└── INITIAL.md
```

---

## Code Standards

### Python
```python
# Type hints required on all functions
def calculate_rsi(prices: list[float], period: int = 14) -> float:
    pass

# Async endpoints
@router.get("/api/screener/signals/today")
async def get_today_signals(db: Session = Depends(get_db)):
    pass

# Use logging not print
import logging
logger = logging.getLogger(__name__)
logger.info("Screener started")
```

### TypeScript
```typescript
// Interfaces required — NO any types
interface Signal {
  id: number;
  symbol: string;
  direction: "CE" | "PE";
  strike: number;
  entryPremium: number;
  slPremium: number;
  t1Premium: number;
  t2Premium: number;
  t3Premium: number;
  confidenceScore: number;
}

const fetchSignals = async (): Promise<Signal[]> => { ... };
```

---

## Risk Rules — NEVER BYPASS THESE

```python
# core/risk.py — these are hardcoded constants
MAX_TRADES_PER_DAY = 2
MAX_CAPITAL_RISK_PCT = 0.02      # 2% per trade
TRADING_CUTOFF_HOUR = 14         # No new trades after 2 PM IST
SL_PCT = 0.40                    # Exit 100% at -40% premium drop
T1_PCT = 0.38                    # +38% → book 30% qty
T2_PCT = 0.79                    # +79% → book 40% qty
T3_PCT = 1.14                    # +114% → book 30% qty (full exit)
QTY_T1, QTY_T2, QTY_T3 = 0.30, 0.40, 0.30
```

All journal endpoints must validate:
- Daily trade count < MAX_TRADES_PER_DAY before allowing new entry
- Current time < 14:00 IST before allowing new entry
- SL field is not null/empty

---

## Database — SQLite (not PostgreSQL)

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../database/tradeguard.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auto-create all tables on startup — no Alembic needed
def init_db():
    Base.metadata.create_all(bind=engine)
```

Call `init_db()` in `main.py` on startup. No Alembic, no migrations.

---

## Scheduler Setup

```python
# main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.screener_service import run_morning_screener

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

@app.on_event("startup")
async def startup():
    init_db()
    scheduler.add_job(run_morning_screener, "cron", hour=9, minute=20)
    scheduler.start()
```

---

## Upstox API Pattern

```python
# services/upstox_client.py
import httpx
from app.config import settings

async def get_options_chain(symbol: str, expiry: str) -> dict:
    headers = {"Authorization": f"Bearer {settings.UPSTOX_ACCESS_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.upstox.com/v2/option/chain",
            params={"instrument_key": symbol, "expiry_date": expiry},
            headers=headers
        )
    return response.json()
```

---

## yfinance Pattern

```python
# services/data_fetcher.py
import yfinance as yf
from datetime import datetime, timedelta

def fetch_historical(symbol: str, days: int = 90) -> list[dict]:
    end = datetime.today()
    start = end - timedelta(days=days)
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval="1d")
    return df.reset_index().to_dict(orient="records")
```

---

## TradingView Webhook Pattern

```python
# routers/webhook.py
from fastapi import APIRouter, Request
from app.services.alert_service import log_alert

router = APIRouter()

@router.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request):
    payload = await request.json()
    await log_alert(payload)
    return {"status": "received"}
```

Expected payload from TradingView Pine Script:
```json
{
  "symbol": "RELIANCE",
  "action": "BUY_CE",
  "price": 2961.5,
  "rsi": 62.4,
  "timestamp": "2026-04-06T09:21:00"
}
```

---

## Forbidden

- `print()` → use `logging`
- Hardcoded API keys → use `.env` + `python-dotenv`
- `any` type in TypeScript
- `console.log` in production code
- PostgreSQL, Alembic, Docker, Redis — not needed for this project
- Auth/JWT/OAuth — not needed, local tool
- Inline styles in React → use Tailwind classes

---

## Environment Variables

```env
# .env
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_ACCESS_TOKEN=your_access_token
VITE_API_URL=http://localhost:8000
```

---

## Skills

| Task | Skill File |
|------|-----------|
| API endpoints | `skills/BACKEND.md` |
| React UI | `skills/FRONTEND.md` |
| SQLite models | `skills/DATABASE.md` |
| Screener + backtest logic | `skills/TRADING.md` |
| Local run setup | `skills/DEPLOYMENT.md` |

---

## Agents

| Agent | Role |
|-------|------|
| DATABASE-AGENT | SQLite models + auto-init |
| BACKEND-AGENT | FastAPI endpoints + screener/backtest services |
| FRONTEND-AGENT | React dashboard + signal cards |
| SCREENER-AGENT | Morning screener + indicator logic |

---

## Workflow

```
1. Fill INITIAL.md
2. /generate-prp INITIAL.md
3. /execute-prp PRPs/tradeguard-prp.md
```

---

## Validation

```bash
# Backend
cd backend && ruff check app/ && pytest

# Frontend
cd frontend && npm run lint && npm run type-check

# Run locally
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```
