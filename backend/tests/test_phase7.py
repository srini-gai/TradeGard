import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        init_db()
        yield c


def test_nifty500_endpoint(client):
    response = client.get("/api/screener/nifty500")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
    # Dynamic list: 50+ (fallback) to 500 (full NSE fetch)
    assert data["count"] >= 50
    assert all("symbol" in s for s in data["symbols"])


def test_nifty500_contains_nifty50(client):
    """Nifty 500 list should contain all Nifty 50 stocks."""
    response = client.get("/api/screener/nifty500")
    symbols = [s["symbol"] for s in response.json()["symbols"]]
    assert "RELIANCE" in symbols
    assert "TCS" in symbols
    assert "HDFCBANK" in symbols


def test_nifty500_contains_midcaps(client):
    """Should include mid-cap stocks beyond Nifty 50."""
    response = client.get("/api/screener/nifty500")
    symbols = [s["symbol"] for s in response.json()["symbols"]]
    assert "ZOMATO" in symbols or "DMART" in symbols or "HAL" in symbols


def test_nifty500_refresh_endpoint(client):
    """Refresh endpoint should return status and count."""
    response = client.post("/api/screener/nifty500/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "refreshed"
    assert data["count"] >= 50
    assert "message" in data


def test_analyse_invalid_symbol(client):
    """Symbol not in Nifty 500 should return 404."""
    response = client.get("/api/screener/analyse/FAKESTOCKXYZ")
    assert response.status_code == 404
    # Error message should mention refresh endpoint
    assert "refresh" in response.json()["detail"].lower()


def test_analyse_valid_symbol(client):
    """Valid Nifty 500 symbol should return analysis."""
    response = client.get("/api/screener/analyse/RELIANCE")
    assert response.status_code == 200
    data = response.json()
    assert "qualified" in data
    assert "symbol" in data
    assert data["symbol"] == "RELIANCE"
    assert "confidence_score" in data
    assert "rsi" in data
    assert "ema20" in data
    assert "reason" in data


def test_analyse_returns_signal_if_qualified(client):
    """If stock qualifies, signal should be present with required fields."""
    response = client.get("/api/screener/analyse/RELIANCE")
    data = response.json()
    if data["qualified"]:
        assert data["signal"] is not None
        assert "entry_premium" in data["signal"]
        assert "t1_premium" in data["signal"]
        assert "direction" in data["signal"]


def test_analyse_not_qualified_has_reason(client):
    """Reason field should always be present and non-empty."""
    response = client.get("/api/screener/analyse/RELIANCE")
    data = response.json()
    assert data["reason"] is not None
    assert len(data["reason"]) > 0


def test_analyse_mcx(client):
    """MCX should be findable and analysable (not 404)."""
    response = client.get("/api/screener/analyse/MCX")
    # 200 = analysis succeeded; 503 = yfinance data unavailable; not 404
    assert response.status_code in (200, 503)


def test_analyse_case_insensitive(client):
    """Symbol lookup should be case-insensitive."""
    response = client.get("/api/screener/analyse/reliance")
    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"


def test_is_valid_nifty500():
    from data.nifty500 import is_valid_nifty500
    assert is_valid_nifty500("RELIANCE") is True
    assert is_valid_nifty500("MCX") is True
    assert is_valid_nifty500("FAKESTOCKXYZ") is False


def test_nifty500_no_duplicates(client):
    response = client.get("/api/screener/nifty500")
    symbols = [s["symbol"] for s in response.json()["symbols"]]
    assert len(symbols) == len(set(symbols))


def test_get_yf_symbol():
    from data.nifty500 import get_yf_symbol
    assert get_yf_symbol("MCX") == "MCX.NS"
    assert get_yf_symbol("M&M") == "M&M.NS"
    assert get_yf_symbol("RELIANCE") == "RELIANCE.NS"
    assert get_yf_symbol("BAJAJ-AUTO") == "BAJAJ-AUTO.NS"
