import logging

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
