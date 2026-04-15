import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

MAX_TRADES_PER_DAY: int = 2
MAX_CAPITAL_RISK_PCT: float = 0.02
TRADING_CUTOFF_HOUR: int = 14

SL_PCT: float = 0.40
T1_GAIN_PCT: float = 0.38
T2_GAIN_PCT: float = 0.79
T3_GAIN_PCT: float = 1.14

QTY_T1: float = 0.30
QTY_T2: float = 0.40
QTY_T3: float = 0.30

MIN_SCORE: int = 60


def calculate_targets(entry_premium: float) -> dict:
    return {
        "sl": round(entry_premium * (1 - SL_PCT), 2),
        "t1": round(entry_premium * (1 + T1_GAIN_PCT), 2),
        "t2": round(entry_premium * (1 + T2_GAIN_PCT), 2),
        "t3": round(entry_premium * (1 + T3_GAIN_PCT), 2),
    }


def is_trading_allowed(today_trade_count: int, current_hour: int) -> tuple[bool, str]:
    if current_hour >= TRADING_CUTOFF_HOUR:
        return False, "No new trades after 2:00 PM IST"
    if today_trade_count >= MAX_TRADES_PER_DAY:
        return False, f"Max {MAX_TRADES_PER_DAY} trades already taken today"
    return True, "OK"


# ---------------------------------------------------------------------------
# Intraday-specific risk constants
# ---------------------------------------------------------------------------
INTRADAY_SL_PCT: float = 0.25
INTRADAY_T1_GAIN_PCT: float = 0.30
INTRADAY_T2_GAIN_PCT: float = 0.60
INTRADAY_EXIT_HOUR: int = 15
INTRADAY_EXIT_MINUTE: int = 0
INTRADAY_QTY_T1: float = 0.40
INTRADAY_QTY_T2: float = 0.60


def calculate_intraday_targets(entry_premium: float) -> dict:
    return {
        "sl": round(entry_premium * (1 - INTRADAY_SL_PCT), 2),
        "t1": round(entry_premium * (1 + INTRADAY_T1_GAIN_PCT), 2),
        "t2": round(entry_premium * (1 + INTRADAY_T2_GAIN_PCT), 2),
    }


def get_weekly_expiry(ref_date: date | None = None) -> date:
    """Returns nearest Thursday (weekly expiry) that is strictly in the future."""
    today = ref_date or date.today()
    days_ahead = 3 - today.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)
