import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.intraday_screener import run_intraday_screener
from app.database import get_db
from app.models.signal import IntradaySignal

router = APIRouter(prefix="/api/intraday", tags=["intraday"])
logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

_running = False


@router.post("/scan")
async def scan_intraday(db: Session = Depends(get_db)):
    """
    Run intraday screener on demand.
    Fetches 30-min candles from Upstox and returns top 2 signals.
    Returns 409 if a scan is already in progress.
    """
    global _running
    if _running:
        raise HTTPException(
            status_code=409, detail="Scan already running — please wait"
        )

    _running = True
    try:
        signals = await run_intraday_screener()

        now = datetime.now(IST).replace(tzinfo=None)
        for s in signals:
            signal = IntradaySignal(
                symbol=s["symbol"],
                signal_date=date.today(),
                scan_time=now,
                direction=s["direction"],
                strike=s["strike"],
                expiry=date.fromisoformat(s["expiry"]),
                entry_premium=s["entry_premium"],
                sl_premium=s["sl_premium"],
                t1_premium=s["t1_premium"],
                t2_premium=s["t2_premium"],
                confidence_score=s["confidence_score"],
                rationale=s.get("rationale", []),
                current_price=s.get("current_price"),
                vwap=s.get("vwap"),
                rsi=s.get("rsi"),
            )
            db.add(signal)
        db.commit()

        return {
            "status": "complete",
            "signals_found": len(signals),
            "signals": signals,
            "scanned_at": now.isoformat(),
            "timeframe": "30min",
            "expiry_type": "weekly",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Intraday scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _running = False


@router.get("/signals/today")
def get_today_signals(db: Session = Depends(get_db)):
    """Return intraday signals generated today, sorted by confidence score."""
    signals = (
        db.query(IntradaySignal)
        .filter(IntradaySignal.signal_date == date.today())
        .order_by(IntradaySignal.confidence_score.desc())
        .all()
    )
    return {
        "date": date.today().isoformat(),
        "count": len(signals),
        "signals": [
            {
                "id": s.id,
                "symbol": s.symbol,
                "direction": s.direction,
                "strike": s.strike,
                "expiry": s.expiry.isoformat(),
                "entry_premium": s.entry_premium,
                "sl_premium": s.sl_premium,
                "t1_premium": s.t1_premium,
                "t2_premium": s.t2_premium,
                "confidence_score": s.confidence_score,
                "rationale": s.rationale,
                "current_price": s.current_price,
                "vwap": s.vwap,
                "rsi": s.rsi,
                "scan_time": s.scan_time.isoformat(),
                "timeframe": s.timeframe,
                "expiry_type": s.expiry_type,
                "exit_by": "15:00 IST",
            }
            for s in signals
        ],
    }


@router.get("/status")
def intraday_status():
    """Check whether the market is open and intraday scanning is available."""
    now_ist = datetime.now(IST)
    market_open = now_ist.weekday() < 5 and (
        (9 <= now_ist.hour < 15) or (now_ist.hour == 15 and now_ist.minute <= 30)
    )
    return {
        "market_open": market_open,
        "current_time_ist": now_ist.strftime("%H:%M"),
        "scan_available": market_open,
        "exit_cutoff": "15:00 IST",
        "timeframe": "30min",
        "expiry": "weekly",
        "message": "Market open — scan available" if market_open else "Market closed",
    }
