import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.signal import Signal
from app.schemas.signal import SignalResponse, ScreenerRunResponse
from app.services.screener_service import run_screener as _run
from app.services.screener_service import save_signals

router = APIRouter(prefix="/api/screener", tags=["screener"])
logger = logging.getLogger(__name__)


@router.post("/run", response_model=ScreenerRunResponse)
def run_screener_now(db: Session = Depends(get_db)):
    """
    Manually trigger the screener. Runs synchronously and returns signals.
    Also persists results to DB.
    """
    logger.info("Manual screener run triggered")
    try:
        signals = _run()
        save_signals(signals, db)
        return ScreenerRunResponse(
            status="complete",
            signals_found=len(signals),
            signals=signals,
            run_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Screener run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Screener failed: {str(e)}") from e


@router.get("/signals/today")
def get_today_signals(db: Session = Depends(get_db)):
    """Return signals generated today."""
    today = date.today()
    signals = (
        db.query(Signal)
        .filter(Signal.signal_date == today)
        .order_by(Signal.confidence_score.desc())
        .all()
    )
    return {
        "date": today.isoformat(),
        "count": len(signals),
        "signals": [SignalResponse.model_validate(s).model_dump() for s in signals],
    }


@router.get("/signals")
def get_all_signals(
    limit: int = 20,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """Return all past signals paginated."""
    signals = (
        db.query(Signal)
        .order_by(Signal.signal_date.desc(), Signal.confidence_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    total = db.query(Signal).count()
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "signals": [SignalResponse.model_validate(s).model_dump() for s in signals],
    }


@router.get("/signals/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Return a single signal by ID."""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
