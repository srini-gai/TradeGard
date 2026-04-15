import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_volume_ratio,
    estimate_premium_bs,
    is_bearish_rsi,
    is_bullish_rsi,
)
from app.core.risk import (
    calculate_intraday_targets,
    get_weekly_expiry,
)
from app.services.upstox_client import get_options_chain_sync, is_upstox_configured
from app.services.upstox_intraday import (
    INTRADAY_FNO_STOCKS,
    calculate_vwap,
    fetch_30min_candles,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
MIN_SCORE = 60
MAX_SIGNALS = 2


async def score_symbol_intraday(symbol: str, instrument_key: str) -> dict | None:
    """
    Run intraday screener logic on a single symbol using 30-min candles.
    Returns signal dict or None if the stock does not qualify.
    """
    try:
        df = await fetch_30min_candles(instrument_key)
        if df.empty or len(df) < 10:
            return None

        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        current_price = float(close.iloc[-1])

        # Indicators on 30-min data
        rsi = calculate_rsi(close, period=14)
        ema9 = calculate_ema(close, period=9)
        ema21 = calculate_ema(close, period=21)
        vol_ratio = calculate_volume_ratio(volume, period=5)
        vwap = calculate_vwap(df)

        if rsi < 0 or ema9 < 0:
            return None

        # Direction: price vs VWAP AND EMA crossover must agree
        above_vwap = current_price > vwap if vwap > 0 else None
        ema_bullish = ema9 > ema21

        if above_vwap is True and ema_bullish:
            direction = "CE"
        elif above_vwap is False and not ema_bullish:
            direction = "PE"
        else:
            return None  # Mixed signals — skip

        score = 30  # base for clear trend alignment
        rationale: list[str] = []

        # VWAP filter — 25 points
        if direction == "CE":
            score += 25
            rationale.append(f"Above VWAP ({vwap:.0f})")
        else:
            score += 25
            rationale.append(f"Below VWAP ({vwap:.0f})")

        # RSI filter — 25 points (mandatory)
        if direction == "CE" and is_bullish_rsi(rsi):
            score += 25
            rationale.append(f"RSI {rsi} bullish")
        elif direction == "PE" and is_bearish_rsi(rsi):
            score += 25
            rationale.append(f"RSI {rsi} bearish")
        else:
            return None  # RSI not confirming direction

        # Volume filter — up to 20 points
        if vol_ratio >= 1.5:
            score += 20
            rationale.append(f"Volume surge {vol_ratio}x")
        elif vol_ratio >= 1.2:
            score += 10
            rationale.append(f"Volume elevated {vol_ratio}x")

        # EMA crossover bonus — 10 points
        if direction == "CE":
            score += 10
            rationale.append(f"EMA9 > EMA21 (bullish cross)")
        else:
            score += 10
            rationale.append(f"EMA9 < EMA21 (bearish cross)")

        if score < MIN_SCORE:
            return None

        # ATM strike — round to nearest 50
        strike = round(current_price / 50) * 50
        expiry = get_weekly_expiry()
        dte = (expiry - date.today()).days

        # Try live Upstox premium first
        entry_premium: float | None = None
        if is_upstox_configured():
            try:
                chain = get_options_chain_sync(symbol, expiry.strftime("%Y-%m-%d"))
                if chain and chain.get("strikes"):
                    for s in chain["strikes"]:
                        if s["strike"] == strike:
                            entry_premium = (
                                s["ce"]["ltp"] if direction == "CE" else s["pe"]["ltp"]
                            )
                            break
                    if not entry_premium:
                        entry_premium = (
                            chain.get("atm_ce_ltp")
                            if direction == "CE"
                            else chain.get("atm_pe_ltp")
                        )
            except Exception:
                pass

        # Fallback to Black-Scholes
        if not entry_premium or entry_premium <= 0:
            entry_premium = estimate_premium_bs(current_price, strike, direction, max(dte, 1))

        targets = calculate_intraday_targets(entry_premium)

        return {
            "symbol": symbol,
            "direction": direction,
            "strike": strike,
            "expiry": expiry.isoformat(),
            "entry_premium": entry_premium,
            "sl_premium": targets["sl"],
            "t1_premium": targets["t1"],
            "t2_premium": targets["t2"],
            "confidence_score": min(score, 100),
            "rationale": rationale,
            "current_price": round(current_price, 2),
            "rsi": rsi,
            "vwap": vwap,
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "volume_ratio": vol_ratio,
            "timeframe": "30min",
            "expiry_type": "weekly",
            "exit_by": "15:00 IST",
        }

    except Exception as e:
        logger.error(f"Intraday score error for {symbol}: {e}")
        return None


async def run_intraday_screener() -> list[dict]:
    """
    Scan all F&O eligible stocks on 30-min chart.
    Returns top MAX_SIGNALS signals sorted by confidence score.
    """
    now_ist = datetime.now(IST)
    logger.info(f"Intraday screener started at {now_ist.strftime('%H:%M IST')}")

    # Only run on weekdays during market hours (9:15 AM – 3:30 PM IST)
    if now_ist.weekday() >= 5:
        logger.info("Weekend — intraday screener skipped")
        return []
    market_open = (9 <= now_ist.hour < 15) or (
        now_ist.hour == 15 and now_ist.minute <= 30
    )
    if not market_open:
        logger.info("Market closed — intraday screener skipped")
        return []

    tasks = [
        score_symbol_intraday(symbol, instrument_key)
        for symbol, instrument_key in INTRADAY_FNO_STOCKS.items()
    ]

    scored = await asyncio.gather(*tasks, return_exceptions=True)

    results = [r for r in scored if isinstance(r, dict)]
    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    top = results[:MAX_SIGNALS]

    logger.info(
        f"Intraday screener: {len(results)} qualified, returning top {len(top)}"
    )
    return top
