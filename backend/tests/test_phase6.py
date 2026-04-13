import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        init_db()
        yield c


# --- Webhook tests ---

def test_webhook_receives_valid_payload(client):
    payload = {
        "symbol": "RELIANCE",
        "action": "BUY_CE",
        "price": 2961.5,
        "rsi": 62.4,
        "timestamp": "2026-04-12T09:21:00",
    }
    response = client.post("/webhook/tradingview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["symbol"] == "RELIANCE"
    assert data["action"] == "BUY_CE"
    assert "alert_id" in data


def test_webhook_unknown_action_still_saves(client):
    payload = {"symbol": "TCS", "action": "CUSTOM_SIGNAL", "price": 3500.0}
    response = client.post("/webhook/tradingview", json=payload)
    assert response.status_code == 200


def test_webhook_missing_fields_still_saves(client):
    """Webhook should accept minimal payload."""
    response = client.post("/webhook/tradingview", json={"symbol": "INFY"})
    assert response.status_code == 200


def test_webhook_invalid_json(client):
    response = client.post(
        "/webhook/tradingview",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_webhook_test_endpoint(client):
    response = client.post("/webhook/test", json={"symbol": "TEST", "action": "ALERT"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "test alert saved"
    assert "alert_id" in data


# --- Alerts API tests ---

def test_alerts_today(client):
    response = client.get("/api/alerts/today")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "count" in data


def test_alerts_all(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data


def test_alerts_with_symbol_filter(client):
    # First create an alert
    client.post("/webhook/tradingview", json={"symbol": "WIPRO", "action": "BUY_PE", "price": 300.0})
    response = client.get("/api/alerts?symbol=WIPRO")
    assert response.status_code == 200
    data = response.json()
    assert all(a["symbol"] == "WIPRO" for a in data["alerts"])


def test_alerts_not_found(client):
    response = client.get("/api/alerts/99999")
    assert response.status_code == 404


def test_alert_saved_to_db(client):
    """After webhook, alert should appear in GET /api/alerts."""
    payload = {"symbol": "HDFCBANK", "action": "BUY_CE", "price": 1700.0, "rsi": 58.0}
    post_res = client.post("/webhook/tradingview", json=payload)
    alert_id = post_res.json()["alert_id"]
    get_res = client.get(f"/api/alerts/{alert_id}")
    assert get_res.status_code == 200
    assert get_res.json()["symbol"] == "HDFCBANK"
    assert get_res.json()["price"] == 1700.0


# --- Risk status ---

def test_risk_status_structure(client):
    response = client.get("/api/journal/risk/status")
    assert response.status_code == 200
    data = response.json()
    required = ["trades_today", "max_trades", "slots_remaining", "trading_window_open"]
    for key in required:
        assert key in data


# --- Health + docs ---

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_docs_accessible(client):
    response = client.get("/docs")
    assert response.status_code == 200
