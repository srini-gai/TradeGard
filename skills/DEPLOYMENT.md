# Deployment Skill — Local Run Only

> TradeGuard is a personal local tool. No Docker, no VPS, no cloud needed.
> Just run backend + frontend locally on your machine.

---

## Requirements

```bash
# Python 3.11+
python --version

# Node 18+
node --version

# Install backend deps
cd backend && pip install -r requirements.txt

# Install frontend deps
cd frontend && npm install
```

---

## Backend Requirements

```txt
# backend/requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
pydantic==2.7.1
pydantic-settings==2.2.1
python-dotenv==1.0.1
yfinance==0.2.40
pandas==2.2.2
numpy==1.26.4
httpx==0.27.0
apscheduler==3.10.4
scipy==1.13.0
python-multipart==0.0.9
ruff==0.4.4
pytest==8.2.0
pytest-asyncio==0.23.6
```

---

## Environment Setup

```env
# .env (in project root — never commit this)
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_ACCESS_TOKEN=your_access_token_here
VITE_API_URL=http://localhost:8000
```

---

## Running Locally

### Terminal 1 — Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
Swagger docs at: http://localhost:8000/docs

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## SQLite Database

No setup needed. Database auto-creates on first backend run at:

```
database/tradeguard.db
```

To reset the database:

```bash
rm database/tradeguard.db
# Restart backend — it recreates all tables automatically
```

To inspect the database:

```bash
# Install SQLite browser (optional)
# Or use command line:
sqlite3 database/tradeguard.db
.tables
SELECT * FROM signals LIMIT 5;
.quit
```

---

## Running the Screener Manually

```bash
# Trigger screener via API (useful for testing outside 9:20 AM)
curl -X POST http://localhost:8000/api/screener/run

# Check today's signals
curl http://localhost:8000/api/screener/signals/today
```

---

## Running a Backtest Manually

```bash
# Trigger backtest (runs async, takes 1-2 minutes)
curl -X POST http://localhost:8000/api/backtest/run

# Check results
curl http://localhost:8000/api/backtest/summary
```

---

## TradingView Webhook Setup

Since you're running locally, use **ngrok** to expose your local backend to TradingView:

```bash
# Install ngrok (one time)
# Download from https://ngrok.com

# Expose backend port
ngrok http 8000

# You get a public URL like:
# https://abc123.ngrok.io

# In TradingView alert → Webhook URL:
# https://abc123.ngrok.io/webhook/tradingview
```

Webhook payload to configure in TradingView alert message:
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

## Scheduler Behaviour

The morning screener is scheduled via APScheduler to run at **9:20 AM IST** every weekday.

```python
# Runs automatically — no manual trigger needed during market hours
scheduler.add_job(
    run_morning_screener,
    "cron",
    hour=9,
    minute=20,
    day_of_week="mon-fri",
    timezone="Asia/Kolkata"
)
```

To test the scheduler trigger immediately:

```bash
curl -X POST http://localhost:8000/api/screener/run
```

---

## Vite Frontend Config

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/webhook': 'http://localhost:8000'
    }
  }
})
```

---

## Common Issues

| Issue | Fix |
|-------|-----|
| `check_same_thread` SQLite error | Already handled in `database.py` |
| Scheduler not triggering | Ensure `Asia/Kolkata` timezone is set |
| yfinance rate limit | Add `time.sleep(0.5)` between symbol fetches |
| Upstox token expired | Regenerate access token from Upstox developer portal |
| CORS error on frontend | Add `CORSMiddleware` in `main.py` |

---

## CORS Setup (Required)

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Validation

```bash
# Check backend is healthy
curl http://localhost:8000/health

# Check frontend builds without errors
cd frontend && npm run build

# Run backend tests
cd backend && pytest

# Lint backend
cd backend && ruff check app/
```
