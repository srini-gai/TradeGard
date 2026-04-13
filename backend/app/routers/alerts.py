import logging
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertResponse  # noqa: F401 — available for future use

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)


def _serialize(a: Alert) -> dict:
    return {
        "id": a.id,
        "symbol": a.symbol,
        "action": a.action,
        "price": a.price,
        "rsi": a.rsi,
        "received_at": a.received_at.isoformat(),
        "source": a.source,
        "payload": a.payload,
    }


@router.get("/today")
def get_today_alerts(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    alerts = (
        db.query(Alert)
        .filter(Alert.received_at >= today_start)
        .order_by(Alert.received_at.desc())
        .all()
    )
    return {"count": len(alerts), "alerts": [_serialize(a) for a in alerts]}


@router.get("")
def get_all_alerts(
    limit: int = Query(default=50, le=200),
    skip: int = 0,
    symbol: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if symbol:
        q = q.filter(Alert.symbol == symbol.upper())
    alerts = q.order_by(Alert.received_at.desc()).offset(skip).limit(limit).all()
    total = db.query(Alert).count()
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "alerts": [_serialize(a) for a in alerts],
    }


@router.get("/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _serialize(alert)


@router.delete("/clear/test")
def clear_test_alerts(db: Session = Depends(get_db)):
    """Remove all test alerts (source='test'). Useful for cleanup."""
    count = db.query(Alert).filter(Alert.source == "test").delete()
    db.commit()
    return {"deleted": count}
