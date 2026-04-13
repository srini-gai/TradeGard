import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_get_trading_days():
    from datetime import date

    from app.core.backtester import get_trading_days

    start = date(2026, 4, 7)
    end = date(2026, 4, 13)
    days = get_trading_days(start, end)
    assert len(days) == 4
    for d in days:
        assert d.weekday() < 5


def test_get_trading_days_excludes_weekends():
    from datetime import date

    from app.core.backtester import get_trading_days

    start = date(2026, 4, 6)
    end = date(2026, 4, 13)
    days = get_trading_days(start, end)
    for d in days:
        assert d.weekday() < 5


def test_max_drawdown_zero():
    from app.core.backtester import _max_drawdown

    assert _max_drawdown([10.0, 20.0, 30.0]) == 0.0


def test_max_drawdown_calculated():
    from app.core.backtester import _max_drawdown

    dd = _max_drawdown([10.0, 20.0, -20.0, -10.0])
    assert dd > 0


def test_calculate_pnl_sl():
    from app.core.backtester import _calculate_pnl

    pnl = _calculate_pnl("SL", True, False, False, False)
    assert pnl == pytest.approx(-40.0, abs=0.1)


def test_calculate_pnl_t1():
    from app.core.backtester import _calculate_pnl

    pnl = _calculate_pnl("T1", False, True, False, False)
    assert pnl > 0


def test_calculate_pnl_t3():
    from app.core.backtester import _calculate_pnl

    pnl = _calculate_pnl("T3", False, True, True, True)
    assert pnl > 50


def test_calculate_pnl_expired():
    from app.core.backtester import _calculate_pnl

    pnl = _calculate_pnl("EXPIRED", False, False, False, False)
    assert pnl == 0.0


def test_backtest_summary_empty(client: TestClient):
    response = client.get("/api/backtest/summary")
    assert response.status_code == 200
    data = response.json()
    assert "has_results" in data


def test_backtest_all_runs_empty(client: TestClient):
    response = client.get("/api/backtest/results")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_backtest_run_not_found(client: TestClient):
    response = client.get("/api/backtest/results/99999")
    assert response.status_code == 404


def test_backtest_months_validation(client: TestClient):
    response = client.post("/api/backtest/run?months=10")
    assert response.status_code == 400


def test_backtest_months_zero(client: TestClient):
    response = client.post("/api/backtest/run?months=0")
    assert response.status_code == 400
