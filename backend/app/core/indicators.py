import calendar
import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_rsi(closes: pd.Series, period: int = 14) -> float:
    """Calculate RSI. Returns -1.0 on failure."""
    try:
        if len(closes) < period + 1:
            return -1.0
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        avg_loss_safe = avg_loss.clip(lower=1e-10)
        rs = avg_gain / avg_loss_safe
        rsi = 100 - (100 / (1 + rs))
        val = float(rsi.iloc[-1])
        return round(val, 2) if not np.isnan(val) else -1.0
    except Exception as e:
        logger.error(f"RSI calc error: {e}")
        return -1.0


def calculate_ema(closes: pd.Series, period: int = 20) -> float:
    """Calculate EMA. Returns -1.0 on failure."""
    try:
        if len(closes) < period:
            return -1.0
        ema = closes.ewm(span=period, adjust=False).mean()
        val = float(ema.iloc[-1])
        return round(val, 2) if not np.isnan(val) else -1.0
    except Exception as e:
        logger.error(f"EMA calc error: {e}")
        return -1.0


def calculate_volume_ratio(volumes: pd.Series, period: int = 10) -> float:
    """Returns today's volume as ratio of N-day average. Returns 0.0 on failure."""
    try:
        if len(volumes) < period + 1:
            return 0.0
        avg_volume = float(volumes.iloc[-period - 1 : -1].mean())
        today_volume = float(volumes.iloc[-1])
        if avg_volume == 0:
            return 0.0
        return round(today_volume / avg_volume, 2)
    except Exception as e:
        logger.error(f"Volume ratio error: {e}")
        return 0.0


def is_above_ema(close: float, ema: float) -> bool:
    return close > ema and ema > 0


def is_bullish_rsi(rsi: float) -> bool:
    return 55.0 <= rsi <= 70.0


def is_bearish_rsi(rsi: float) -> bool:
    return 30.0 <= rsi <= 45.0


def is_volume_surge(volume_ratio: float, threshold: float = 1.5) -> bool:
    return volume_ratio >= threshold


def estimate_premium_bs(
    spot: float,
    strike: float,
    direction: str,
    days_to_expiry: int = 15,
    iv: float = 0.20,
    r: float = 0.065,
) -> float:
    """
    Estimate ATM/OTM option premium using Black-Scholes.
    Used when live Upstox options chain is unavailable.
    direction: 'CE' or 'PE'
    Returns minimum ₹1.0 to avoid zero premium edge cases.
    """
    import math

    from scipy.stats import norm

    try:
        T = max(days_to_expiry, 1) / 365.0
        S, K = float(spot), float(strike)
        if S <= 0 or K <= 0:
            return 1.0

        d1 = (math.log(S / K) + (r + 0.5 * iv**2) * T) / (iv * math.sqrt(T))
        d2 = d1 - iv * math.sqrt(T)

        if direction == "CE":
            premium = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            premium = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

        return round(max(float(premium), 1.0), 2)
    except Exception as e:
        logger.error(f"Black-Scholes error: {e}")
        return 1.0


def get_monthly_expiry(ref_date: date | None = None) -> date:
    """
    Returns last Thursday of the current month.
    If that Thursday has already passed, returns last Thursday of next month.
    """
    today = ref_date or date.today()
    year, month = today.year, today.month

    def last_thursday(y: int, m: int) -> date:
        last_day = calendar.monthrange(y, m)[1]
        for day in range(last_day, last_day - 7, -1):
            if date(y, m, day).weekday() == 3:
                return date(y, m, day)
        raise RuntimeError(f"No Thursday in month {m}/{y}")

    expiry = last_thursday(year, month)
    if expiry <= today:
        month = month % 12 + 1
        year = year + (1 if month == 1 else 0)
        expiry = last_thursday(year, month)

    return expiry


def days_to_expiry(ref_date: date | None = None) -> int:
    """Returns number of calendar days from today to monthly expiry."""
    today = ref_date or date.today()
    expiry = get_monthly_expiry(today)
    return max((expiry - today).days, 1)
