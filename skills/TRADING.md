# Trading Skill — Screener, Backtester & Risk Rules

> This skill defines all trading logic for TradeGuard.
> Read this before building screener.py, backtester.py, or indicators.py.

---

## Nifty 50 Symbols

```python
# data/nifty50.py
NIFTY50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "BAJFINANCE.NS", "WIPRO.NS", "HCLTECH.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
    "TECHM.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "POWERGRID.NS", "NTPC.NS",
    "ONGC.NS", "COALINDIA.NS", "ADANIPORTS.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS", "DRREDDY.NS", "CIPLA.NS",
    "DIVISLAB.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "BRITANNIA.NS",
    "INDUSINDBK.NS", "GRASIM.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "BPCL.NS",
    "LTIM.NS", "HINDALCO.NS", "VEDL.NS", "SHRIRAMFIN.NS", "ADANIENT.NS"
]

# NSE symbol format (without .NS) for Upstox API
NSE_SYMBOLS = [s.replace(".NS", "") for s in NIFTY50_SYMBOLS]
```

---

## Risk Constants

```python
# core/risk.py
MAX_TRADES_PER_DAY = 2
MAX_CAPITAL_RISK_PCT = 0.02      # 2% of capital per trade
TRADING_CUTOFF_HOUR = 14         # No new trades after 2:00 PM IST

# Stop loss
SL_PCT = 0.40                    # Exit 100% if premium drops 40%

# Profit booking ladder
T1_GAIN_PCT = 0.38               # +38% premium gain
T2_GAIN_PCT = 0.79               # +79% premium gain
T3_GAIN_PCT = 1.14               # +114% premium gain

# Qty to book at each level
QTY_T1 = 0.30                    # Book 30% of position
QTY_T2 = 0.40                    # Book 40% of position
QTY_T3 = 0.30                    # Book remaining 30%

# SL adjustment after T1 hit
SL_AFTER_T1 = "ENTRY"            # Move SL to entry price (risk-free)
SL_AFTER_T2 = T1_GAIN_PCT        # Trail SL to T1 level

def calculate_targets(entry_premium: float) -> dict:
    return {
        "sl": round(entry_premium * (1 - SL_PCT), 2),
        "t1": round(entry_premium * (1 + T1_GAIN_PCT), 2),
        "t2": round(entry_premium * (1 + T2_GAIN_PCT), 2),
        "t3": round(entry_premium * (1 + T3_GAIN_PCT), 2),
    }

def is_trading_allowed(db, current_hour: int) -> tuple[bool, str]:
    """Check if a new trade is allowed right now."""
    if current_hour >= TRADING_CUTOFF_HOUR:
        return False, "Trading cutoff reached — no new trades after 2 PM IST"
    today_count = get_today_trade_count(db)
    if today_count >= MAX_TRADES_PER_DAY:
        return False, f"Max {MAX_TRADES_PER_DAY} trades already taken today"
    return True, "OK"
```

---

## Technical Indicators

```python
# core/indicators.py
import pandas as pd
import numpy as np

def calculate_rsi(closes: pd.Series, period: int = 14) -> float:
    """Returns current RSI value."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)

def calculate_ema(closes: pd.Series, period: int = 20) -> float:
    """Returns current EMA value."""
    ema = closes.ewm(span=period, adjust=False).mean()
    return round(float(ema.iloc[-1]), 2)

def calculate_volume_ratio(volumes: pd.Series, period: int = 10) -> float:
    """Returns today's volume as ratio of N-day average."""
    avg_volume = volumes.iloc[-period-1:-1].mean()
    today_volume = volumes.iloc[-1]
    return round(float(today_volume / avg_volume), 2)

def is_above_ema(close: float, ema: float) -> bool:
    return close > ema

def is_bullish_rsi(rsi: float) -> bool:
    return 55 <= rsi <= 70

def is_bearish_rsi(rsi: float) -> bool:
    return 30 <= rsi <= 45

def is_volume_surge(volume_ratio: float, threshold: float = 1.5) -> bool:
    return volume_ratio >= threshold
```

---

## Morning Screener Logic

```python
# core/screener.py
import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
from app.core.indicators import (
    calculate_rsi, calculate_ema, calculate_volume_ratio,
    is_above_ema, is_bullish_rsi, is_bearish_rsi, is_volume_surge
)
from app.core.risk import calculate_targets
from app.data.nifty50 import NIFTY50_SYMBOLS

def score_stock(symbol: str) -> dict | None:
    """
    Run all filters on a stock. Returns signal dict if qualifies, else None.
    Score is 0-100 based on how many filters pass and their strength.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="3mo", interval="1d")
        if df.empty or len(df) < 20:
            return None

        close = df["Close"]
        volume = df["Volume"]
        current_price = float(close.iloc[-1])

        rsi = calculate_rsi(close)
        ema20 = calculate_ema(close)
        volume_ratio = calculate_volume_ratio(volume)
        above_ema = is_above_ema(current_price, ema20)

        score = 0
        direction = None
        rationale = []

        # Trend filter (30 points)
        if above_ema:
            direction = "CE"
            score += 30
            rationale.append(f"Above 20 EMA ({ema20:.0f})")
        else:
            direction = "PE"
            score += 30
            rationale.append(f"Below 20 EMA ({ema20:.0f})")

        # RSI filter (30 points)
        if direction == "CE" and is_bullish_rsi(rsi):
            score += 30
            rationale.append(f"RSI {rsi} (bullish zone 55-70)")
        elif direction == "PE" and is_bearish_rsi(rsi):
            score += 30
            rationale.append(f"RSI {rsi} (bearish zone 30-45)")
        else:
            return None  # RSI doesn't confirm direction — skip

        # Volume filter (25 points)
        if is_volume_surge(volume_ratio):
            score += 25
            rationale.append(f"Volume {volume_ratio}x avg (surge)")
        elif volume_ratio >= 1.2:
            score += 10
            rationale.append(f"Volume {volume_ratio}x avg (mild)")

        # Minimum score threshold
        if score < 60:
            return None

        # Estimate ATM strike (round to nearest 50)
        strike = round(current_price / 50) * 50
        entry_premium = estimate_premium(current_price, strike, direction)
        targets = calculate_targets(entry_premium)

        # Estimated timelines (rough — based on momentum)
        today = date.today()

        return {
            "symbol": symbol.replace(".NS", ""),
            "signal_date": today,
            "direction": direction,
            "strike": strike,
            "expiry": get_monthly_expiry(today),
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
            "current_price": current_price,
            "rsi": rsi,
            "ema20": ema20,
            "volume_ratio": volume_ratio,
        }

    except Exception as e:
        return None


def run_screener() -> list[dict]:
    """
    Scan all 50 Nifty stocks. Return top 2 signals sorted by confidence score.
    """
    results = []
    for symbol in NIFTY50_SYMBOLS:
        signal = score_stock(symbol)
        if signal:
            results.append(signal)

    # Sort by confidence score descending, return top 2
    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    return results[:2]


def get_monthly_expiry(today: date) -> date:
    """Returns the last Thursday of the current month."""
    import calendar
    year, month = today.year, today.month
    # Find last Thursday
    last_day = calendar.monthrange(year, month)[1]
    last_thursday = max(
        day for day in range(last_day, last_day - 7, -1)
        if date(year, month, day).weekday() == 3  # Thursday
    )
    expiry = date(year, month, last_thursday)
    # If expiry already passed, use next month
    if expiry < today:
        month = month % 12 + 1
        year = year + (1 if month == 1 else 0)
        last_day = calendar.monthrange(year, month)[1]
        last_thursday = max(
            day for day in range(last_day, last_day - 7, -1)
            if date(year, month, day).weekday() == 3
        )
        expiry = date(year, month, last_thursday)
    return expiry


def estimate_premium(spot: float, strike: float, direction: str) -> float:
    """
    Rough ATM premium estimate using simplified Black-Scholes approximation.
    Used when live Upstox options chain is unavailable.
    IV assumed at 20% for most large-cap stocks.
    """
    import math
    T = 15 / 365        # ~15 trading days to expiry
    r = 0.065           # risk-free rate
    sigma = 0.20        # assumed IV 20%
    S = spot
    K = strike

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    from scipy.stats import norm
    if direction == "CE":
        premium = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        premium = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return round(max(premium, 1.0), 2)
```

---

## Backtesting Engine

```python
# core/backtester.py
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from app.core.screener import score_stock, get_monthly_expiry, estimate_premium
from app.core.risk import SL_PCT, T1_GAIN_PCT, T2_GAIN_PCT, T3_GAIN_PCT
from app.core.risk import QTY_T1, QTY_T2, QTY_T3
from app.data.nifty50 import NIFTY50_SYMBOLS

def run_backtest(months: int = 3) -> dict:
    """
    Replay last N months of trading days.
    For each day, run screener logic and simulate trade execution.
    Returns summary with win rate and P&L stats.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    all_trades = []
    monthly_pnl = {}

    # Get all trading days in range
    trading_days = get_trading_days(start_date, end_date)

    for trade_date in trading_days:
        # Simulate screener on this date
        daily_signals = simulate_screener_on_date(trade_date)

        for signal in daily_signals[:2]:  # Max 2 per day
            outcome = simulate_trade(signal, trade_date)
            if outcome:
                all_trades.append(outcome)
                month_key = trade_date.strftime("%b %Y")
                if month_key not in monthly_pnl:
                    monthly_pnl[month_key] = {"trades": 0, "pnl": 0.0, "wins": 0}
                monthly_pnl[month_key]["trades"] += 1
                monthly_pnl[month_key]["pnl"] += outcome["pnl_pct"]
                if outcome["pnl_pct"] > 0:
                    monthly_pnl[month_key]["wins"] += 1

    if not all_trades:
        return {"error": "No trades generated in backtest period"}

    pnls = [t["pnl_pct"] for t in all_trades]
    wins = [t for t in all_trades if t["pnl_pct"] > 0]

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_signals": len(all_trades),
        "win_rate": round(len(wins) / len(all_trades) * 100, 1),
        "avg_pnl": round(sum(pnls) / len(pnls), 1),
        "best_trade_pnl": round(max(pnls), 1),
        "worst_trade_pnl": round(min(pnls), 1),
        "max_drawdown": calculate_max_drawdown(pnls),
        "monthly_breakdown": monthly_pnl,
        "trades": all_trades,
    }


def simulate_trade(signal: dict, entry_date: date) -> dict | None:
    """
    Simulate a trade from entry_date forward.
    Check each subsequent day if SL/T1/T2/T3 was hit.
    Uses daily OHLC as proxy for intraday premium movement.
    """
    symbol = signal["symbol"] + ".NS"
    entry_premium = signal["entry_premium"]
    direction = signal["direction"]

    sl = entry_premium * (1 - SL_PCT)
    t1 = entry_premium * (1 + T1_GAIN_PCT)
    t2 = entry_premium * (1 + T2_GAIN_PCT)
    t3 = entry_premium * (1 + T3_GAIN_PCT)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=entry_date + timedelta(days=1),
            end=entry_date + timedelta(days=20),
            interval="1d"
        )
    except Exception:
        return None

    if df.empty:
        return None

    t1_hit = t2_hit = t3_hit = sl_hit = False
    exit_premium = entry_premium
    outcome = "EXPIRED"
    pnl_pct = 0.0

    for _, row in df.iterrows():
        # Estimate daily high/low premium from stock price movement
        daily_high_prem = estimate_premium(float(row["High"]), signal["strike"], direction)
        daily_low_prem = estimate_premium(float(row["Low"]), signal["strike"], direction)

        if not t1_hit and daily_high_prem >= t1:
            t1_hit = True
        if t1_hit and not t2_hit and daily_high_prem >= t2:
            t2_hit = True
        if t2_hit and not t3_hit and daily_high_prem >= t3:
            t3_hit = True
            outcome = "T3"
            break
        if not t1_hit and daily_low_prem <= sl:
            sl_hit = True
            outcome = "SL"
            exit_premium = sl
            break

    # Calculate blended P&L based on what was hit
    if outcome == "T3":
        pnl_pct = (QTY_T1 * T1_GAIN_PCT + QTY_T2 * T2_GAIN_PCT + QTY_T3 * T3_GAIN_PCT) * 100
    elif t2_hit:
        outcome = "T2"
        pnl_pct = (QTY_T1 * T1_GAIN_PCT + QTY_T2 * T2_GAIN_PCT - QTY_T3 * SL_PCT) * 100
    elif t1_hit:
        outcome = "T1"
        pnl_pct = (QTY_T1 * T1_GAIN_PCT - (QTY_T2 + QTY_T3) * 0) * 100  # SL moved to entry
    elif sl_hit:
        pnl_pct = -SL_PCT * 100

    return {
        "symbol": signal["symbol"],
        "direction": direction,
        "entry_date": entry_date.isoformat(),
        "entry_premium": entry_premium,
        "outcome": outcome,
        "pnl_pct": round(pnl_pct, 1),
    }


def simulate_screener_on_date(trade_date: date) -> list[dict]:
    """Run screener logic using only data available up to trade_date."""
    results = []
    for symbol in NIFTY50_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=trade_date - timedelta(days=60),
                end=trade_date,
                interval="1d"
            )
            if df.empty or len(df) < 20:
                continue

            # Run indicators on historical slice
            from app.core.indicators import (
                calculate_rsi, calculate_ema, calculate_volume_ratio
            )
            rsi = calculate_rsi(df["Close"])
            ema20 = calculate_ema(df["Close"])
            vol_ratio = calculate_volume_ratio(df["Volume"])
            current_price = float(df["Close"].iloc[-1])
            above_ema = current_price > ema20

            score = 0
            direction = "CE" if above_ema else "PE"
            score += 30

            from app.core.indicators import is_bullish_rsi, is_bearish_rsi
            if direction == "CE" and is_bullish_rsi(rsi):
                score += 30
            elif direction == "PE" and is_bearish_rsi(rsi):
                score += 30
            else:
                continue

            if vol_ratio >= 1.5:
                score += 25

            if score < 60:
                continue

            strike = round(current_price / 50) * 50
            entry_premium = estimate_premium(current_price, strike, direction)

            results.append({
                "symbol": symbol.replace(".NS", ""),
                "direction": direction,
                "strike": strike,
                "entry_premium": entry_premium,
                "confidence_score": score,
            })

        except Exception:
            continue

    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    return results[:2]


def get_trading_days(start: date, end: date) -> list[date]:
    """Return list of weekdays (Mon-Fri) between start and end."""
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday=0, Friday=4
            days.append(current)
        current += timedelta(days=1)
    return days


def calculate_max_drawdown(pnl_pcts: list[float]) -> float:
    """Calculate maximum peak-to-trough drawdown from list of trade P&Ls."""
    if not pnl_pcts:
        return 0.0
    cumulative = []
    total = 0
    for p in pnl_pcts:
        total += p
        cumulative.append(total)
    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        drawdown = peak - val
        if drawdown > max_dd:
            max_dd = drawdown
    return round(max_dd, 1)
```

---

## Lot Sizes Reference

```python
# data/lot_sizes.py — NSE F&O lot sizes (update periodically)
LOT_SIZES = {
    "RELIANCE": 250, "TCS": 150, "HDFCBANK": 550, "INFY": 300,
    "ICICIBANK": 700, "HINDUNILVR": 300, "ITC": 1600, "SBIN": 1500,
    "BHARTIARTL": 950, "KOTAKBANK": 400, "LT": 150, "AXISBANK": 625,
    "ASIANPAINT": 200, "MARUTI": 100, "TITAN": 375, "BAJFINANCE": 125,
    "WIPRO": 1500, "HCLTECH": 350, "ULTRACEMCO": 100, "NESTLEIND": 50,
    "TECHM": 600, "SUNPHARMA": 350, "TATAMOTORS": 1425, "POWERGRID": 2900,
    "NTPC": 2250, "ONGC": 1925, "COALINDIA": 1400, "ADANIPORTS": 625,
    "JSWSTEEL": 675, "TATASTEEL": 3375, "BAJAJFINSV": 125, "SBILIFE": 375,
    "HDFCLIFE": 1000, "DRREDDY": 125, "CIPLA": 650, "DIVISLAB": 100,
    "EICHERMOT": 175, "HEROMOTOCO": 150, "BAJAJ-AUTO": 75, "BRITANNIA": 100,
    "INDUSINDBK": 500, "GRASIM": 375, "TATACONSUM": 900, "APOLLOHOSP": 125,
    "BPCL": 1800, "LTIM": 150, "HINDALCO": 1400, "VEDL": 2000,
    "SHRIRAMFIN": 300, "ADANIENT": 325,
}

def get_lot_size(symbol: str) -> int:
    return LOT_SIZES.get(symbol.upper(), 500)
```

---

## Best Practices

- Always fetch data with `try/except` — yfinance can fail silently
- Add `time.sleep(0.3)` between yfinance calls during backtesting to avoid rate limits
- Black-Scholes premium estimates are approximations — real premiums will differ
- RSI period 14 is standard — do not change
- EMA period 20 is the primary trend filter — do not change
- Volume ratio threshold 1.5x is minimum — higher is better
- Always use `date.today()` in IST timezone for scheduling
- Monthly expiry = last Thursday of the month
