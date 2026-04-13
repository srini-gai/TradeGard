import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from data.nifty50 import NIFTY50_SYMBOLS

logger = logging.getLogger(__name__)

_MAX_FETCH_ATTEMPTS = 3
_FETCH_RETRY_DELAY_SEC = 1.5


def fetch_historical(symbol: str, days: int = 90) -> pd.DataFrame:
    """Fetch OHLCV data for a single symbol. Returns empty DataFrame on failure."""
    end = datetime.today()
    start = end - timedelta(days=days)
    last_error: Exception | None = None
    for attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, interval="1d")
            if df.empty:
                logger.warning(f"No data returned for {symbol} (attempt {attempt})")
            else:
                return df
        except Exception as e:
            last_error = e
            logger.warning(f"Fetch attempt {attempt}/{_MAX_FETCH_ATTEMPTS} failed for {symbol}: {e}")
        if attempt < _MAX_FETCH_ATTEMPTS:
            time.sleep(_FETCH_RETRY_DELAY_SEC)
    if last_error:
        logger.error(f"Failed to fetch {symbol}: {last_error}")
    return pd.DataFrame()


def fetch_all_nifty50(days: int = 90) -> dict[str, pd.DataFrame]:
    """
    Fetch historical data for all 50 Nifty stocks.
    Adds a small delay between calls to avoid rate limiting.
    """
    results = {}
    total = len(NIFTY50_SYMBOLS)
    for i, symbol in enumerate(NIFTY50_SYMBOLS):
        logger.info(f"Fetching {symbol} ({i + 1}/{total})")
        df = fetch_historical(symbol, days)
        if not df.empty:
            results[symbol] = df
        time.sleep(0.3)
    logger.info(f"Fetched data for {len(results)}/{total} symbols")
    return results


def fetch_current_price(symbol: str) -> float | None:
    """Fetch latest closing price for a symbol."""
    last_error: Exception | None = None
    for attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2d", interval="1d")
            if df.empty:
                logger.warning(f"No price data for {symbol} (attempt {attempt})")
            else:
                return round(float(df["Close"].iloc[-1]), 2)
        except Exception as e:
            last_error = e
            logger.warning(
                f"Price fetch attempt {attempt}/{_MAX_FETCH_ATTEMPTS} failed for {symbol}: {e}"
            )
        if attempt < _MAX_FETCH_ATTEMPTS:
            time.sleep(_FETCH_RETRY_DELAY_SEC)
    if last_error:
        logger.error(f"Failed to get price for {symbol}: {last_error}")
    return None
