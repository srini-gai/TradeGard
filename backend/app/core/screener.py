import logging
import time
from datetime import date, timedelta

import pandas as pd

from app.core.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_volume_ratio,
    days_to_expiry,
    estimate_premium_bs,
    get_monthly_expiry,
    is_above_ema,
    is_bearish_rsi,
    is_bullish_rsi,
    is_volume_surge,
)
from app.core.risk import MIN_SCORE, calculate_targets
from app.services.data_fetcher import fetch_historical
from data.nifty50 import NIFTY50_SYMBOLS

logger = logging.getLogger(__name__)

MAX_SIGNALS = 2


def _index_row_dates(index: pd.Index) -> pd.Series:
    """Normalize index to Python dates for comparison with ref_date."""
    out: list[date] = []
    for ts in index:
        t = pd.Timestamp(ts)
        if t.tzinfo is not None:
            t = t.tz_convert("Asia/Kolkata")
        out.append(t.date())
    return pd.Series(out, index=index)


def score_symbol(symbol: str, ref_date: date | None = None) -> dict | None:
    """
    Run all screener filters on a single symbol.
    Returns a signal dict if score >= MIN_SCORE, else None.
    ref_date: used during backtesting to limit data to a past date.
    """
    try:
        df = fetch_historical(symbol, days=90)
        if df.empty or len(df) < 25:
            return None

        if ref_date:
            row_dates = _index_row_dates(df.index)
            df = df[row_dates <= ref_date]
            if len(df) < 25:
                return None

        close = df["Close"].astype(float)
        volume = df["Volume"].astype(float)
        current_price = float(close.iloc[-1])

        rsi = calculate_rsi(close)
        ema20 = calculate_ema(close)
        vol_ratio = calculate_volume_ratio(volume)

        if rsi < 0 or ema20 < 0:
            return None

        above_ema = is_above_ema(current_price, ema20)
        direction = "CE" if above_ema else "PE"

        score = 0
        rationale = []

        score += 30
        if direction == "CE":
            rationale.append(f"Above 20 EMA (EMA: {ema20:.0f})")
        else:
            rationale.append(f"Below 20 EMA (EMA: {ema20:.0f})")

        if direction == "CE" and is_bullish_rsi(rsi):
            score += 30
            rationale.append(f"RSI {rsi} — bullish zone (55–70)")
        elif direction == "PE" and is_bearish_rsi(rsi):
            score += 30
            rationale.append(f"RSI {rsi} — bearish zone (30–45)")
        else:
            return None

        if is_volume_surge(vol_ratio):
            score += 25
            rationale.append(f"Volume surge {vol_ratio}x avg")
        elif vol_ratio >= 1.2:
            score += 10
            rationale.append(f"Volume elevated {vol_ratio}x avg")

        if score < MIN_SCORE:
            return None

        strike = round(current_price / 50) * 50

        today = ref_date or date.today()
        dte = days_to_expiry(today)
        entry_premium = estimate_premium_bs(current_price, strike, direction, dte)
        targets = calculate_targets(entry_premium)
        expiry = get_monthly_expiry(today)

        return {
            "symbol": symbol.replace(".NS", ""),
            "signal_date": today,
            "direction": direction,
            "strike": float(strike),
            "expiry": expiry,
            "entry_premium": entry_premium,
            "sl_premium": targets["sl"],
            "t1_premium": targets["t1"],
            "t2_premium": targets["t2"],
            "t3_premium": targets["t3"],
            "t1_date": today + timedelta(days=4),
            "t2_date": today + timedelta(days=9),
            "t3_date": today + timedelta(days=14),
            "confidence_score": min(score, 100),
            "rationale": rationale,
            "current_price": round(current_price, 2),
            "rsi": rsi,
            "ema20": ema20,
            "volume_ratio": vol_ratio,
            "days_to_expiry": dte,
        }

    except Exception as e:
        logger.error(f"Error scoring {symbol}: {e}")
        return None


def run_screener(ref_date: date | None = None) -> list[dict]:
    """
    Scan all 50 Nifty stocks. Return top MAX_SIGNALS signals by confidence score.
    ref_date: for backtesting — limits data to that date.
    """
    logger.info(f"Running screener for date: {ref_date or date.today()}")
    results = []

    for symbol in NIFTY50_SYMBOLS:
        signal = score_symbol(symbol, ref_date)
        if signal:
            results.append(signal)
        time.sleep(0.2)

    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    top = results[:MAX_SIGNALS]

    logger.info(
        f"Screener complete — {len(results)} qualified, returning top {len(top)}"
    )
    return top
