import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.risk import (
    MAX_TRADES_PER_DAY,
    QTY_T1,
    QTY_T2,
    QTY_T3,
    TRADING_CUTOFF_HOUR,
)
from app.models.trade import PartialBooking, Trade
from app.schemas.trade import BookingRequest, TradeCreate
from data.lot_sizes import get_lot_size

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def _ist_now() -> datetime:
    return datetime.now(IST)


def _today_ist() -> date:
    return _ist_now().date()


def _count_today_trades(db: Session) -> int:
    today_start = datetime.combine(_today_ist(), datetime.min.time())
    return db.query(Trade).filter(Trade.entry_date >= today_start).count()


def _check_trading_rules(db: Session) -> tuple[bool, str]:
    now_ist = _ist_now()
    if now_ist.hour >= TRADING_CUTOFF_HOUR:
        return (
            False,
            f"Trading cutoff reached — no new trades after {TRADING_CUTOFF_HOUR}:00 IST",
        )
    count = _count_today_trades(db)
    if count >= MAX_TRADES_PER_DAY:
        return False, f"Max {MAX_TRADES_PER_DAY} trades already logged today"
    return True, "OK"


def log_trade(
    payload: TradeCreate, db: Session, bypass_time_check: bool = False
) -> Trade:
    if not bypass_time_check:
        allowed, reason = _check_trading_rules(db)
        if not allowed:
            raise ValueError(reason)

    lot_size = payload.lot_size if payload.lot_size > 0 else get_lot_size(
        payload.symbol
    )

    trade = Trade(
        symbol=payload.symbol.upper(),
        direction=payload.direction,
        strike=payload.strike,
        expiry=payload.expiry,
        entry_date=_ist_now().replace(tzinfo=None),
        entry_premium=payload.entry_premium,
        lots=payload.lots,
        lot_size=lot_size,
        sl_premium=payload.sl_premium,
        t1_premium=payload.t1_premium,
        t2_premium=payload.t2_premium,
        t3_premium=payload.t3_premium,
        status="OPEN",
        notes=payload.notes,
        signal_id=payload.signal_id,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    logger.info(
        f"Trade logged: {trade.symbol} {trade.direction} {trade.strike} id={trade.id}"
    )
    return trade


def book_partial(trade_id: int, req: BookingRequest, db: Session) -> Trade:
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise ValueError(f"Trade {trade_id} not found")
    if trade.status in ("CLOSED", "SL_HIT"):
        raise ValueError(f"Trade {trade_id} is already {trade.status}")

    level = req.level
    exit_premium = req.exit_premium
    total_qty = trade.lots * trade.lot_size

    dup = (
        db.query(PartialBooking)
        .filter(
            PartialBooking.trade_id == trade_id,
            PartialBooking.level == level,
        )
        .first()
    )
    if dup:
        raise ValueError(f"Level {level} already booked for this trade")

    level_qty_map = {
        "T1": round(total_qty * QTY_T1),
        "T2": round(total_qty * QTY_T2),
        "T3": round(total_qty * QTY_T3),
        "SL": total_qty,
    }
    qty = level_qty_map[level]

    if level == "SL":
        booked_so_far = (
            db.query(func.coalesce(func.sum(PartialBooking.qty_booked), 0))
            .filter(PartialBooking.trade_id == trade_id)
            .scalar()
        )
        booked_so_far = int(booked_so_far or 0)
        remaining = total_qty - booked_so_far
        if remaining <= 0:
            raise ValueError("No open quantity left to book as SL")
        qty = remaining

    pnl = (exit_premium - trade.entry_premium) * qty

    booking = PartialBooking(
        trade_id=trade_id,
        level=level,
        booked_at=_ist_now().replace(tzinfo=None),
        qty_booked=qty,
        exit_premium=exit_premium,
        pnl=round(pnl, 2),
    )
    db.add(booking)

    if level == "SL":
        trade.status = "SL_HIT"
        trade.exit_premium = exit_premium
        prev_sum = (
            db.query(func.coalesce(func.sum(PartialBooking.pnl), 0.0))
            .filter(PartialBooking.trade_id == trade_id)
            .scalar()
        )
        trade.total_pnl = round(float(prev_sum or 0) + booking.pnl, 2)
    elif level == "T3":
        trade.status = "CLOSED"
        trade.exit_premium = exit_premium
        prev_sum = (
            db.query(func.coalesce(func.sum(PartialBooking.pnl), 0.0))
            .filter(PartialBooking.trade_id == trade_id)
            .scalar()
        )
        trade.total_pnl = round(float(prev_sum or 0) + booking.pnl, 2)
    else:
        trade.status = "PARTIAL"

    db.commit()
    db.refresh(trade)
    logger.info(
        f"Booked {level} on trade {trade_id} at ₹{exit_premium}, P&L={pnl:.2f}"
    )
    return trade


def get_trades(db: Session, limit: int = 50, skip: int = 0) -> list[Trade]:
    return (
        db.query(Trade)
        .options(selectinload(Trade.bookings))
        .order_by(Trade.entry_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_today_trades(db: Session) -> list[Trade]:
    today_start = datetime.combine(_today_ist(), datetime.min.time())
    return (
        db.query(Trade)
        .options(selectinload(Trade.bookings))
        .filter(Trade.entry_date >= today_start)
        .order_by(Trade.entry_date.desc())
        .all()
    )


def get_trade_by_id(trade_id: int, db: Session) -> Trade | None:
    return (
        db.query(Trade)
        .options(selectinload(Trade.bookings))
        .filter(Trade.id == trade_id)
        .first()
    )


def get_monthly_summary(db: Session) -> dict:
    today = _today_ist()
    month_start = datetime(today.year, today.month, 1)
    trades = db.query(Trade).filter(Trade.entry_date >= month_start).all()
    if not trades:
        return {
            "period": today.strftime("%b %Y"),
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "sl_hit": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "best_trade_pnl": None,
            "worst_trade_pnl": None,
        }

    closed = [
        t
        for t in trades
        if t.status in ("CLOSED", "SL_HIT") and t.total_pnl is not None
    ]
    wins = [t for t in closed if t.total_pnl and t.total_pnl > 0]
    pnls = [t.total_pnl for t in closed if t.total_pnl is not None]

    return {
        "period": today.strftime("%b %Y"),
        "total_trades": len(trades),
        "open_trades": len([t for t in trades if t.status == "OPEN"]),
        "closed_trades": len([t for t in trades if t.status == "CLOSED"]),
        "sl_hit": len([t for t in trades if t.status == "SL_HIT"]),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
        "total_pnl": round(sum(pnls), 2),
        "best_trade_pnl": round(max(pnls), 2) if pnls else None,
        "worst_trade_pnl": round(min(pnls), 2) if pnls else None,
    }


def get_weekly_summary(db: Session) -> dict:
    today = _today_ist()
    week_start = datetime.combine(
        today - timedelta(days=today.weekday()),
        datetime.min.time(),
    )
    trades = db.query(Trade).filter(Trade.entry_date >= week_start).all()
    closed = [
        t
        for t in trades
        if t.status in ("CLOSED", "SL_HIT") and t.total_pnl is not None
    ]
    pnls = [t.total_pnl for t in closed if t.total_pnl is not None]
    wins = [t for t in closed if t.total_pnl and t.total_pnl > 0]

    return {
        "period": f"Week of {week_start.strftime('%d %b %Y')}",
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
        "total_pnl": round(sum(pnls), 2) if pnls else 0.0,
    }
