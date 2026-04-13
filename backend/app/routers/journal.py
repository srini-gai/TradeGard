from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.risk import MAX_TRADES_PER_DAY, TRADING_CUTOFF_HOUR
from app.database import get_db
from app.schemas.trade import BookingRequest, TradeCreate, TradeResponse
from app.services.journal_service import (
    _check_trading_rules,
    _count_today_trades,
    book_partial,
    get_monthly_summary,
    get_today_trades,
    get_trade_by_id,
    get_trades,
    get_weekly_summary,
    log_trade,
)

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.post("/trades", response_model=TradeResponse)
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    try:
        return log_trade(payload, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/trades", response_model=list[TradeResponse])
def list_trades(limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    return get_trades(db, limit=limit, skip=skip)


@router.get("/trades/today", response_model=list[TradeResponse])
def today_trades(db: Session = Depends(get_db)):
    return get_today_trades(db)


@router.get("/trades/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = get_trade_by_id(trade_id, db)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/trades/{trade_id}/book", response_model=TradeResponse)
def book_level(trade_id: int, req: BookingRequest, db: Session = Depends(get_db)):
    try:
        return book_partial(trade_id, req, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/summary/monthly")
def monthly_summary(db: Session = Depends(get_db)):
    return get_monthly_summary(db)


@router.get("/summary/weekly")
def weekly_summary(db: Session = Depends(get_db)):
    return get_weekly_summary(db)


@router.get("/risk/status")
def risk_status(db: Session = Depends(get_db)):
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    allowed, reason = _check_trading_rules(db)
    count = _count_today_trades(db)
    return {
        "trades_today": count,
        "max_trades": MAX_TRADES_PER_DAY,
        "slots_remaining": max(0, MAX_TRADES_PER_DAY - count),
        "trading_window_open": allowed,
        "cutoff_hour_ist": TRADING_CUTOFF_HOUR,
        "current_hour_ist": now_ist.hour,
        "reason": reason if not allowed else "OK",
    }
