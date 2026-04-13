from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_rsi_calculation():
    from app.core.indicators import calculate_rsi

    prices = pd.Series([float(100 + i) for i in range(30)])
    rsi = calculate_rsi(prices)
    assert 0 < rsi <= 100


def test_ema_calculation():
    from app.core.indicators import calculate_ema

    prices = pd.Series([float(100 + i * 0.5) for i in range(30)])
    ema = calculate_ema(prices, period=20)
    assert ema > 0


def test_volume_ratio():
    from app.core.indicators import calculate_volume_ratio

    vols = pd.Series([1000.0] * 10 + [2000.0])
    ratio = calculate_volume_ratio(vols, period=10)
    assert ratio == pytest.approx(2.0, abs=0.1)


def test_premium_estimate():
    from app.core.indicators import estimate_premium_bs

    premium = estimate_premium_bs(
        spot=2960, strike=3000, direction="CE", days_to_expiry=15
    )
    assert premium >= 1.0


def test_monthly_expiry_is_thursday():
    from app.core.indicators import get_monthly_expiry

    expiry = get_monthly_expiry(date.today())
    assert expiry.weekday() == 3


def test_monthly_expiry_in_future():
    from app.core.indicators import get_monthly_expiry

    expiry = get_monthly_expiry(date.today())
    assert expiry > date.today()


def test_calculate_targets():
    from app.core.risk import calculate_targets

    targets = calculate_targets(100.0)
    assert targets["sl"] == pytest.approx(60.0, abs=0.1)
    assert targets["t1"] == pytest.approx(138.0, abs=0.1)
    assert targets["t2"] == pytest.approx(179.0, abs=0.1)
    assert targets["t3"] == pytest.approx(214.0, abs=0.1)


def test_trading_allowed():
    from app.core.risk import is_trading_allowed

    ok, _msg = is_trading_allowed(0, 9)
    assert ok is True


def test_trading_cutoff():
    from app.core.risk import is_trading_allowed

    ok, msg = is_trading_allowed(0, 14)
    assert ok is False
    assert "2:00 PM" in msg


def test_max_trades_limit():
    from app.core.risk import is_trading_allowed

    ok, _msg = is_trading_allowed(2, 9)
    assert ok is False


def test_screener_signals_today_empty(client: TestClient):
    response = client.get("/api/screener/signals/today")
    assert response.status_code == 200
    data = response.json()
    assert "signals" in data
    assert isinstance(data["signals"], list)


def test_screener_all_signals(client: TestClient):
    response = client.get("/api/screener/signals")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "signals" in data


def test_screener_signal_not_found(client: TestClient):
    response = client.get("/api/screener/signals/99999")
    assert response.status_code == 404


def test_score_single_symbol():
    from app.core.screener import score_symbol

    result = score_symbol("RELIANCE.NS")
    if result is not None:
        assert "symbol" in result
        assert "direction" in result
        assert result["direction"] in ("CE", "PE")
        assert result["confidence_score"] >= 60
        assert result["entry_premium"] >= 1.0
