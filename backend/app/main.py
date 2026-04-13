import asyncio
import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import alerts, backtest, data, journal, screener, webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

_SCHEDULER_ENABLED = os.environ.get("TRADEGUARD_SCHEDULER", "1").lower() in (
    "1",
    "true",
    "yes",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    logger.info("Database initialised")

    # Pre-load Nifty 500 symbol cache (non-blocking)
    try:
        from data.nifty500 import get_nifty500_symbols
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, get_nifty500_symbols)
        logger.info("Nifty 500 symbol list loaded")
    except Exception as e:
        logger.warning(f"Nifty 500 pre-load failed: {e} — will load on first request")

    if _SCHEDULER_ENABLED:
        from app.services.screener_service import run_morning_screener

        scheduler.add_job(
            run_morning_screener,
            "cron",
            hour=9,
            minute=20,
            day_of_week="mon-fri",
            timezone="Asia/Kolkata",
            id="morning_screener",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Scheduler started — screener runs at 9:20 AM IST on weekdays"
        )
    else:
        logger.info("APScheduler disabled (set TRADEGUARD_SCHEDULER=1 to enable)")

    logger.info("TradeGuard API started")

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(
    title="TradeGuard API",
    description="Personal options trading assistant for Nifty 50 stocks",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(screener.router)
app.include_router(backtest.router)
app.include_router(journal.router)
app.include_router(webhook.router)
app.include_router(alerts.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "TradeGuard API",
        "version": "1.0.0",
    }


@app.get("/")
def root():
    return {"message": "TradeGuard API — visit /docs for Swagger UI"}
