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
    is_above_ema,
    is_bearish_rsi,
    is_bullish_rsi,
    is_volume_surge,
)
from app.core.risk import (
    MIN_SCORE,
    QTY_T1,
    QTY_T2,
    QTY_T3,
    SL_PCT,
    T1_GAIN_PCT,
    T2_GAIN_PCT,
    T3_GAIN_PCT,
)
from app.services.data_fetcher import fetch_historical
from data.nifty50 import NIFTY50_SYMBOLS

logger = logging.getLogger(__name__)

MAX_SIGNALS_PER_DAY = 2
MAX_HOLD_DAYS = 20


def _row_dates(idx: pd.Index) -> pd.Series:
    out: list[date] = []
    for ts in idx:
        t = pd.Timestamp(ts)
        if t.tzinfo is not None:
            t = t.tz_convert("Asia/Kolkata")
        out.append(t.date())
    return pd.Series(out, index=idx)


def get_trading_days(start: date, end: date) -> list[date]:
    """Return Mon–Fri dates between start (inclusive) and end (exclusive)."""
    days = []
    current = start
    while current < end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _score_symbol_on_date(symbol: str, df: pd.DataFrame, ref_date: date) -> dict | None:
    """
    Run screener logic on a pre-fetched DataFrame sliced to ref_date.
    Avoids repeated yfinance calls during backtesting.
    """
    try:
        row_dates = _row_dates(df.index)
        mask = row_dates <= ref_date
        slice_df = df.loc[mask]

        if len(slice_df) < 25:
            return None

        close = slice_df["Close"].astype(float)
        volume = slice_df["Volume"].astype(float)
        current_price = float(close.iloc[-1])

        rsi = calculate_rsi(close)
        ema20 = calculate_ema(close)
        vol_ratio = calculate_volume_ratio(volume)

        if rsi < 0 or ema20 < 0:
            return None

        above_ema = is_above_ema(current_price, ema20)
        direction = "CE" if above_ema else "PE"

        score = 30
        if direction == "CE" and is_bullish_rsi(rsi):
            score += 30
        elif direction == "PE" and is_bearish_rsi(rsi):
            score += 30
        else:
            return None

        if is_volume_surge(vol_ratio):
            score += 25
        elif vol_ratio >= 1.2:
            score += 10

        if score < MIN_SCORE:
            return None

        strike = round(current_price / 50) * 50
        dte = days_to_expiry(ref_date)
        entry_premium = estimate_premium_bs(current_price, strike, direction, dte)

        return {
            "symbol": symbol.replace(".NS", ""),
            "direction": direction,
            "strike": float(strike),
            "entry_premium": entry_premium,
            "confidence_score": min(score, 100),
            "current_price": round(current_price, 2),
        }
    except Exception as e:
        logger.debug(f"Score error for {symbol} on {ref_date}: {e}")
        return None


def _simulate_trade(
    signal: dict,
    entry_date: date,
    full_df: pd.DataFrame,
) -> dict:
    """Simulate a trade forward from entry_date using pre-fetched OHLC data."""
    direction = signal["direction"]
    strike = signal["strike"]
    entry_premium = signal["entry_premium"]

    sl = entry_premium * (1 - SL_PCT)
    t1 = entry_premium * (1 + T1_GAIN_PCT)
    t2 = entry_premium * (1 + T2_GAIN_PCT)
    t3 = entry_premium * (1 + T3_GAIN_PCT)

    row_dates = _row_dates(full_df.index)
    future_mask = row_dates > entry_date
    future_df = full_df.loc[future_mask].head(MAX_HOLD_DAYS)

    t1_hit = t2_hit = t3_hit = sl_hit = False
    outcome = "EXPIRED"
    exit_date = entry_date + timedelta(days=MAX_HOLD_DAYS)

    for idx, row in future_df.iterrows():
        ts = pd.Timestamp(idx)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("Asia/Kolkata")
        row_date = ts.date()
        high_price = float(row["High"])
        low_price = float(row["Low"])

        dte_rem = max(1, (exit_date - row_date).days)
        high_prem = estimate_premium_bs(high_price, strike, direction, dte_rem)
        low_prem = estimate_premium_bs(low_price, strike, direction, dte_rem)

        if not t1_hit:
            if low_prem <= sl:
                sl_hit = True
                outcome = "SL"
                exit_date = row_date
                break

        if not t1_hit and high_prem >= t1:
            t1_hit = True

        if t1_hit and not t2_hit and high_prem >= t2:
            t2_hit = True

        if t2_hit and not t3_hit and high_prem >= t3:
            t3_hit = True
            outcome = "T3"
            exit_date = row_date
            break

    if not sl_hit and not t3_hit:
        if t2_hit:
            outcome = "T2"
        elif t1_hit:
            outcome = "T1"

    pnl_pct = _calculate_pnl(outcome, sl_hit, t1_hit, t2_hit, t3_hit)

    return {
        "symbol": signal["symbol"],
        "direction": direction,
        "entry_date": entry_date.isoformat(),
        "exit_date": exit_date.isoformat(),
        "entry_premium": entry_premium,
        "exit_premium": round(entry_premium * (1 + pnl_pct / 100), 2),
        "outcome": outcome,
        "pnl_pct": round(pnl_pct, 1),
        "pnl_abs": round(entry_premium * pnl_pct / 100, 2),
    }


def _calculate_pnl(
    outcome: str,
    sl_hit: bool,
    t1_hit: bool,
    t2_hit: bool,
    t3_hit: bool,
) -> float:
    if outcome == "SL":
        return -SL_PCT * 100

    if outcome == "T3":
        return (
            QTY_T1 * T1_GAIN_PCT + QTY_T2 * T2_GAIN_PCT + QTY_T3 * T3_GAIN_PCT
        ) * 100

    if outcome == "T2":
        return (
            QTY_T1 * T1_GAIN_PCT
            + QTY_T2 * T2_GAIN_PCT
            + QTY_T3 * T1_GAIN_PCT
        ) * 100

    if outcome == "T1":
        return (QTY_T1 * T1_GAIN_PCT + 0.0) * 100

    return 0.0


def run_backtest(months: int = 3) -> dict:
    """
    Replay last N months of trading days.
    Pre-fetches all 50 stocks once, then iterates day by day.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 31)
    trading_days = get_trading_days(start_date, end_date)

    logger.info(
        f"Backtest: {start_date} → {end_date} "
        f"({len(trading_days)} trading days, {len(NIFTY50_SYMBOLS)} symbols)"
    )

    logger.info("Pre-fetching historical data for all 50 symbols...")
    all_data: dict[str, pd.DataFrame] = {}
    for i, symbol in enumerate(NIFTY50_SYMBOLS):
        df = fetch_historical(symbol, days=months * 31 + 30)
        if not df.empty:
            all_data[symbol] = df
        time.sleep(0.2)
        if (i + 1) % 10 == 0:
            logger.info(f"  fetched {i + 1}/{len(NIFTY50_SYMBOLS)}")

    logger.info(f"Data ready for {len(all_data)} symbols. Starting simulation...")

    all_trades: list[dict] = []
    monthly_stats: dict[str, dict] = {}

    for trade_date in trading_days:
        day_signals = []
        for symbol, df in all_data.items():
            sig = _score_symbol_on_date(symbol, df, trade_date)
            if sig:
                day_signals.append(sig)

        day_signals.sort(key=lambda x: x["confidence_score"], reverse=True)
        day_signals = day_signals[:MAX_SIGNALS_PER_DAY]

        for signal in day_signals:
            symbol = signal["symbol"]
            yf_symbol = f"{symbol}.NS"
            if yf_symbol not in all_data:
                continue
            trade = _simulate_trade(signal, trade_date, all_data[yf_symbol])
            all_trades.append(trade)

            month_key = trade_date.strftime("%b %Y")
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {"trades": 0, "pnl_sum": 0.0, "wins": 0}
            monthly_stats[month_key]["trades"] += 1
            monthly_stats[month_key]["pnl_sum"] += trade["pnl_pct"]
            if trade["pnl_pct"] > 0:
                monthly_stats[month_key]["wins"] += 1

    logger.info(f"Simulation complete — {len(all_trades)} trades simulated")

    if not all_trades:
        return {
            "error": "No trades generated in backtest period",
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_signals": 0,
        }

    pnls = [t["pnl_pct"] for t in all_trades]
    wins = [t for t in all_trades if t["pnl_pct"] > 0]

    monthly_breakdown = {}
    for month, stats in monthly_stats.items():
        n = stats["trades"]
        monthly_breakdown[month] = {
            "trades": n,
            "win_rate": round(stats["wins"] / n * 100, 1) if n else 0,
            "avg_pnl": round(stats["pnl_sum"] / n, 1) if n else 0,
        }

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_signals": len(all_trades),
        "win_rate": round(len(wins) / len(all_trades) * 100, 1),
        "avg_pnl": round(sum(pnls) / len(pnls), 1),
        "best_trade_pnl": round(max(pnls), 1),
        "worst_trade_pnl": round(min(pnls), 1),
        "max_drawdown": _max_drawdown(pnls),
        "monthly_breakdown": monthly_breakdown,
        "trades": all_trades,
    }


def _max_drawdown(pnl_pcts: list[float]) -> float:
    if not pnl_pcts:
        return 0.0
    cumulative: list[float] = []
    total = 0.0
    for p in pnl_pcts:
        total += p
        cumulative.append(total)
    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        peak = max(peak, val)
        max_dd = max(max_dd, peak - val)
    return round(max_dd, 1)
