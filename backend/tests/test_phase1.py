import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.database import engine, init_db
from app.main import app


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_nifty50_symbols(client: TestClient):
    response = client.get("/api/data/nifty50")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 50
    assert "RELIANCE" in data["symbols"]


def test_get_price_reliance(client: TestClient):
    response = client.get("/api/data/price/RELIANCE")
    assert response.status_code == 200
    data = response.json()
    assert "price" in data
    assert data["price"] > 0


def test_get_historical_reliance(client: TestClient):
    response = client.get("/api/data/historical/RELIANCE?days=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) > 0


def test_stub_screener(client: TestClient):
    response = client.get("/api/screener/signals/today")
    assert response.status_code == 200
    data = response.json()
    assert "signals" in data
    assert "count" in data


def test_db_tables_created():
    init_db()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "signals" in tables
    assert "trades" in tables
    assert "backtest_runs" in tables
    assert "alerts" in tables
