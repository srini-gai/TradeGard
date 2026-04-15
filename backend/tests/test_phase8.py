import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        init_db()
        yield c


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

def test_intraday_status(client):
    response = client.get("/api/intraday/status")
    assert response.status_code == 200
    data = response.json()
    assert "market_open" in data
    assert "current_time_ist" in data
    assert "scan_available" in data
    assert "exit_cutoff" in data
    assert data["exit_cutoff"] == "15:00 IST"
    assert data["timeframe"] == "30min"
    assert data["expiry"] == "weekly"


def test_intraday_signals_today_empty(client):
    response = client.get("/api/intraday/signals/today")
    assert response.status_code == 200
    data = response.json()
    assert "signals" in data
    assert isinstance(data["signals"], list)
    assert "count" in data
    assert "date" in data


# ---------------------------------------------------------------------------
# Risk constants
# ---------------------------------------------------------------------------

def test_intraday_risk_constants():
    from app.core.risk import (
        INTRADAY_EXIT_HOUR,
        INTRADAY_EXIT_MINUTE,
        INTRADAY_QTY_T1,
        INTRADAY_QTY_T2,
        INTRADAY_SL_PCT,
        INTRADAY_T1_GAIN_PCT,
        INTRADAY_T2_GAIN_PCT,
    )
    assert INTRADAY_SL_PCT == 0.25
    assert INTRADAY_T1_GAIN_PCT == 0.30
    assert INTRADAY_T2_GAIN_PCT == 0.60
    assert INTRADAY_EXIT_HOUR == 15
    assert INTRADAY_EXIT_MINUTE == 0
    assert INTRADAY_QTY_T1 == 0.40
    assert INTRADAY_QTY_T2 == 0.60


def test_intraday_targets():
    from app.core.risk import calculate_intraday_targets

    targets = calculate_intraday_targets(100.0)
    assert targets["sl"] == pytest.approx(75.0, abs=0.1)
    assert targets["t1"] == pytest.approx(130.0, abs=0.1)
    assert targets["t2"] == pytest.approx(160.0, abs=0.1)


def test_intraday_targets_non_round():
    from app.core.risk import calculate_intraday_targets

    targets = calculate_intraday_targets(50.0)
    assert targets["sl"] == pytest.approx(37.5, abs=0.1)
    assert targets["t1"] == pytest.approx(65.0, abs=0.1)
    assert targets["t2"] == pytest.approx(80.0, abs=0.1)


# ---------------------------------------------------------------------------
# Weekly expiry
# ---------------------------------------------------------------------------

def test_weekly_expiry_is_thursday():
    from app.core.risk import get_weekly_expiry

    expiry = get_weekly_expiry()
    assert expiry.weekday() == 3, f"Expected Thursday (3), got {expiry.weekday()}"


def test_weekly_expiry_in_future():
    from datetime import date

    from app.core.risk import get_weekly_expiry

    expiry = get_weekly_expiry()
    assert expiry > date.today(), "Weekly expiry should be strictly in the future"


def test_weekly_expiry_custom_date():
    from datetime import date

    from app.core.risk import get_weekly_expiry

    # Monday 2026-04-13 → nearest upcoming Thursday is 2026-04-16
    result = get_weekly_expiry(date(2026, 4, 13))
    assert result == date(2026, 4, 16)
    assert result.weekday() == 3


def test_weekly_expiry_on_thursday_rolls_to_next():
    from datetime import date

    from app.core.risk import get_weekly_expiry

    # Thursday itself: days_ahead = 3 - 3 = 0, so <=0 → +7 → next Thursday
    result = get_weekly_expiry(date(2026, 4, 16))
    assert result == date(2026, 4, 23)
    assert result.weekday() == 3


# ---------------------------------------------------------------------------
# VWAP calculation
# ---------------------------------------------------------------------------

def test_vwap_calculation():
    import pandas as pd

    from app.services.upstox_intraday import calculate_vwap

    df = pd.DataFrame(
        {
            "high": [100.0, 102.0, 101.0],
            "low": [98.0, 99.0, 99.0],
            "close": [99.0, 101.0, 100.0],
            "volume": [1000.0, 2000.0, 1500.0],
        }
    )
    vwap = calculate_vwap(df)
    assert vwap > 0
    # Typical prices: 99, 100.67, 100; weighted by volume
    expected = (99 * 1000 + 100.67 * 2000 + 100 * 1500) / 4500
    assert vwap == pytest.approx(expected, abs=0.1)


def test_vwap_empty_dataframe():
    import pandas as pd

    from app.services.upstox_intraday import calculate_vwap

    assert calculate_vwap(pd.DataFrame()) == 0.0


def test_vwap_zero_volume():
    import pandas as pd

    from app.services.upstox_intraday import calculate_vwap

    df = pd.DataFrame(
        {
            "high": [100.0],
            "low": [99.0],
            "close": [99.5],
            "volume": [0.0],
        }
    )
    assert calculate_vwap(df) == 0.0


# ---------------------------------------------------------------------------
# FNO stock list
# ---------------------------------------------------------------------------

def test_fno_stocks_not_empty():
    from app.services.upstox_intraday import INTRADAY_FNO_STOCKS

    assert len(INTRADAY_FNO_STOCKS) > 0


def test_fno_stocks_instrument_key_format():
    from app.services.upstox_intraday import INTRADAY_FNO_STOCKS

    for symbol, key in INTRADAY_FNO_STOCKS.items():
        assert key.startswith("NSE_EQ|"), f"{symbol} has invalid instrument key: {key}"
        assert "INE" in key, f"{symbol} key missing ISIN: {key}"


# ---------------------------------------------------------------------------
# DB model
# ---------------------------------------------------------------------------

def test_intraday_signal_model_exists():
    from app.models.signal import IntradaySignal

    assert IntradaySignal.__tablename__ == "intraday_signals"


def test_intraday_table_created(client):
    """Verify the intraday_signals table exists after init_db."""
    from sqlalchemy import inspect

    from app.database import engine

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "intraday_signals" in tables
