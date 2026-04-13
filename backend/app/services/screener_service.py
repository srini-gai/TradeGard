import logging

from sqlalchemy.orm import Session

from app.core.screener import run_screener
from app.database import SessionLocal
from app.models.signal import Signal

logger = logging.getLogger(__name__)

__all__ = ["run_screener", "save_signals", "run_morning_screener"]


def save_signals(signals: list[dict], db: Session) -> list[Signal]:
    """Persist screener output to DB. Skip duplicates (same symbol + date)."""
    saved = []
    for s in signals:
        existing = (
            db.query(Signal)
            .filter(
                Signal.symbol == s["symbol"],
                Signal.signal_date == s["signal_date"],
            )
            .first()
        )
        if existing:
            logger.info(
                f"Signal already exists for {s['symbol']} on {s['signal_date']}, skipping"
            )
            continue

        signal = Signal(
            symbol=s["symbol"],
            signal_date=s["signal_date"],
            direction=s["direction"],
            strike=s["strike"],
            expiry=s["expiry"],
            entry_premium=s["entry_premium"],
            sl_premium=s["sl_premium"],
            t1_premium=s["t1_premium"],
            t2_premium=s["t2_premium"],
            t3_premium=s["t3_premium"],
            t1_date=s.get("t1_date"),
            t2_date=s.get("t2_date"),
            t3_date=s.get("t3_date"),
            confidence_score=s["confidence_score"],
            rationale=s.get("rationale", []),
        )
        db.add(signal)
        saved.append(signal)

    db.commit()
    for sig in saved:
        db.refresh(sig)

    logger.info(f"Saved {len(saved)} new signals to DB")
    return saved


def run_morning_screener() -> list[dict]:
    """
    Called by APScheduler at 9:20 AM IST.
    Runs screener and saves signals to DB.
    """
    logger.info("Morning screener triggered by scheduler")
    db = SessionLocal()
    try:
        signals = run_screener()
        save_signals(signals, db)
        logger.info(f"Morning screener complete — {len(signals)} signals saved")
        return signals
    except Exception as e:
        logger.error(f"Morning screener failed: {e}")
        db.rollback()
        return []
    finally:
        db.close()
