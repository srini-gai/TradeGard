import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models.alert import Alert

router = APIRouter(tags=["webhook"])
logger = logging.getLogger(__name__)

VALID_ACTIONS = {"BUY_CE", "BUY_PE", "EXIT_CE", "EXIT_PE", "EXIT", "ALERT"}


@router.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request, db: Session = Depends(get_db)):
    """
    Receives webhook POST from TradingView Pine Script alerts.
    Saves to alerts table. Returns 200 immediately (TradingView retries on failure).

    Expected payload:
    {
      "symbol": "RELIANCE",
      "action": "BUY_CE",
      "price": 2961.5,
      "rsi": 62.4,
      "timestamp": "2026-04-12T09:21:00"
    }
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    symbol = payload.get("symbol", "UNKNOWN").upper()
    action = payload.get("action", "ALERT").upper()
    price = payload.get("price")
    rsi = payload.get("rsi")

    # Normalize action
    if action not in VALID_ACTIONS:
        logger.warning(f"Unknown action '{action}' from TradingView — saving anyway")

    alert = Alert(
        symbol=symbol,
        action=action,
        price=float(price) if price is not None else None,
        rsi=float(rsi) if rsi is not None else None,
        payload=payload,
        received_at=datetime.now(),
        source="tradingview",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    logger.info(f"TradingView alert received: {symbol} {action} @ {price}")
    return {
        "status": "received",
        "alert_id": alert.id,
        "symbol": symbol,
        "action": action,
    }


@router.post("/webhook/test")
async def test_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Test endpoint — send a fake alert to verify webhook setup.
    POST /webhook/test with any JSON body.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    alert = Alert(
        symbol=payload.get("symbol", "TEST"),
        action=payload.get("action", "ALERT"),
        price=payload.get("price"),
        rsi=payload.get("rsi"),
        payload=payload,
        received_at=datetime.now(),
        source="test",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "status": "test alert saved",
        "alert_id": alert.id,
        "message": "Webhook is working correctly",
    }
