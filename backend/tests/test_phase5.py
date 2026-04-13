import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app
from app.schemas.trade import BookingRequest, TradeCreate
from app.services.journal_service import book_partial, get_monthly_summary, log_trade


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _sample_trade_payload(**overrides) -> dict:
    base = {
        "symbol": "RELIANCE",
        "direction": "CE",
        "strike": 3000.0,
        "expiry": (date.today() + timedelta(days=14)).isoformat(),
        "entry_premium": 50.0,
        "lots": 1,
        "lot_size": 250,
        "sl_premium": 30.0,
        "t1_premium": 69.0,
        "t2_premium": 89.5,
        "t3_premium": 107.0,
        "notes": "test trade",
    }
    base.update(overrides)
    return base


def test_trade_create_invalid_direction(client: TestClient):
    payload = _sample_trade_payload(direction="XX")
    response = client.post("/api/journal/trades", json=payload)
    assert response.status_code == 422


def test_trade_create_invalid_lots(client: TestClient):
    payload = _sample_trade_payload(lots=0)
    response = client.post("/api/journal/trades", json=payload)
    assert response.status_code == 422


def test_booking_invalid_level(client: TestClient):
    response = client.post(
        "/api/journal/trades/1/book",
        json={"level": "T4", "exit_premium": 80.0},
    )
    assert response.status_code == 422


def test_log_trade_service():
    db = SessionLocal()
    try:
        payload = TradeCreate(**_sample_trade_payload())
        trade = log_trade(payload, db, bypass_time_check=True)
        assert trade.id is not None
        assert trade.symbol == "RELIANCE"
        assert trade.status == "OPEN"
        assert trade.lot_size == 250
    finally:
        db.close()


def test_book_t1_service():
    db = SessionLocal()
    try:
        payload = TradeCreate(**_sample_trade_payload())
        trade = log_trade(payload, db, bypass_time_check=True)
        updated = book_partial(
            trade.id, BookingRequest(level="T1", exit_premium=69.0), db
        )
        assert updated.status == "PARTIAL"
        assert len(updated.bookings) == 1
        assert updated.bookings[0].level == "T1"
        assert updated.bookings[0].pnl > 0
    finally:
        db.close()


def test_book_sl_service():
    db = SessionLocal()
    try:
        payload = TradeCreate(**_sample_trade_payload())
        trade = log_trade(payload, db, bypass_time_check=True)
        updated = book_partial(
            trade.id, BookingRequest(level="SL", exit_premium=30.0), db
        )
        assert updated.status == "SL_HIT"
        assert updated.total_pnl is not None
        assert updated.total_pnl < 0
    finally:
        db.close()


def test_book_full_ladder_service():
    db = SessionLocal()
    try:
        payload = TradeCreate(**_sample_trade_payload())
        trade = log_trade(payload, db, bypass_time_check=True)
        book_partial(trade.id, BookingRequest(level="T1", exit_premium=69.0), db)
        book_partial(trade.id, BookingRequest(level="T2", exit_premium=89.5), db)
        final = book_partial(
            trade.id, BookingRequest(level="T3", exit_premium=107.0), db
        )
        assert final.status == "CLOSED"
        assert final.total_pnl is not None
        assert final.total_pnl > 0
        assert len(final.bookings) == 3
    finally:
        db.close()


def test_book_already_closed(client: TestClient):
    db = SessionLocal()
    try:
        payload = TradeCreate(**_sample_trade_payload())
        trade = log_trade(payload, db, bypass_time_check=True)
        book_partial(trade.id, BookingRequest(level="SL", exit_premium=30.0), db)
        response = client.post(
            f"/api/journal/trades/{trade.id}/book",
            json={"level": "T1", "exit_premium": 69.0},
        )
        assert response.status_code == 400
    finally:
        db.close()


def test_monthly_summary_service():
    db = SessionLocal()
    try:
        summary = get_monthly_summary(db)
        assert "period" in summary
        assert "total_trades" in summary
        assert "win_rate" in summary
        assert "total_pnl" in summary
    finally:
        db.close()


def test_get_trades(client: TestClient):
    response = client.get("/api/journal/trades")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_today_trades(client: TestClient):
    response = client.get("/api/journal/trades/today")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_trade_not_found(client: TestClient):
    response = client.get("/api/journal/trades/99999")
    assert response.status_code == 404


def test_monthly_summary_endpoint(client: TestClient):
    response = client.get("/api/journal/summary/monthly")
    assert response.status_code == 200
    data = response.json()
    assert "total_trades" in data
    assert "win_rate" in data


def test_weekly_summary_endpoint(client: TestClient):
    response = client.get("/api/journal/summary/weekly")
    assert response.status_code == 200
    data = response.json()
    assert "total_trades" in data


def test_risk_status_endpoint(client: TestClient):
    response = client.get("/api/journal/risk/status")
    assert response.status_code == 200
    data = response.json()
    assert "trades_today" in data
    assert "trading_window_open" in data
    assert "slots_remaining" in data
