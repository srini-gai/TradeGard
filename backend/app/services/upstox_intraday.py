import logging
from datetime import date, datetime, timedelta

import httpx
import pandas as pd
from zoneinfo import ZoneInfo

from app.config import settings

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
BASE_URL = "https://api.upstox.com/v2"

# Nifty 500 F&O eligible stocks — instrument key format: NSE_EQ|{ISIN}
INTRADAY_FNO_STOCKS: dict[str, str] = {
    "RELIANCE":   "NSE_EQ|INE002A01018",
    "TCS":        "NSE_EQ|INE467B01029",
    "HDFCBANK":   "NSE_EQ|INE040A01034",
    "INFY":       "NSE_EQ|INE009A01021",
    "ICICIBANK":  "NSE_EQ|INE090A01021",
    "SBIN":       "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "KOTAKBANK":  "NSE_EQ|INE237A01028",
    "LT":         "NSE_EQ|INE018A01030",
    "AXISBANK":   "NSE_EQ|INE238A01034",
    "WIPRO":      "NSE_EQ|INE075A01022",
    "HCLTECH":    "NSE_EQ|INE860A01027",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "SUNPHARMA":  "NSE_EQ|INE044A01036",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "MARUTI":     "NSE_EQ|INE585B01010",
    "TITAN":      "NSE_EQ|INE280A01028",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "NTPC":       "NSE_EQ|INE733E01010",
    "POWERGRID":  "NSE_EQ|INE752E01010",
    "ONGC":       "NSE_EQ|INE213A01029",
    "COALINDIA":  "NSE_EQ|INE522F01014",
    "JSWSTEEL":   "NSE_EQ|INE019A01038",
    "TATASTEEL":  "NSE_EQ|INE081A01020",
    "HINDALCO":   "NSE_EQ|INE038A01020",
    "DRREDDY":    "NSE_EQ|INE089A01023",
    "CIPLA":      "NSE_EQ|INE059A01026",
    "DIVISLAB":   "NSE_EQ|INE361B01024",
    "SIEMENS":    "NSE_EQ|INE003A01024",
    "HAVELLS":    "NSE_EQ|INE176B01034",
    "VOLTAS":     "NSE_EQ|INE226A01021",
    "POLYCAB":    "NSE_EQ|INE455K01017",
    "TRENT":      "NSE_EQ|INE849A01020",
    "ZOMATO":     "NSE_EQ|INE758T01015",
    "DMART":      "NSE_EQ|INE192R01011",
    "IRCTC":      "NSE_EQ|INE335Y01020",
    "HAL":        "NSE_EQ|INE066F01020",
    "BEL":        "NSE_EQ|INE263A01024",
    "MPHASIS":    "NSE_EQ|INE356A01018",
    "PERSISTENT": "NSE_EQ|INE262H01021",
    "COFORGE":    "NSE_EQ|INE591G01017",
    "TATAELXSI":  "NSE_EQ|INE670A01012",
    "JUBLFOOD":   "NSE_EQ|INE797F01020",
    "PAGEIND":    "NSE_EQ|INE761H01022",
}


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.upstox_access_token}",
        "Accept": "application/json",
    }


def _today_ist() -> date:
    return datetime.now(IST).date()


def _last_trading_day() -> date:
    """Returns today if a weekday, else the most recent Friday."""
    today = _today_ist()
    if today.weekday() == 5:      # Saturday
        return today - timedelta(days=1)
    elif today.weekday() == 6:    # Sunday
        return today - timedelta(days=2)
    return today


def _previous_trading_day(d: date) -> date:
    """Returns the most recent trading day before d (skips weekends)."""
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return prev


async def fetch_30min_candles(
    instrument_key: str, trade_date: date | None = None
) -> pd.DataFrame:
    """
    Fetch 30-min OHLCV candles from Upstox for a given instrument.
    Fetches yesterday + today to ensure >= 10 candles even early morning.
    Returns DataFrame with columns: timestamp, open, high, low, close, volume, oi
    Empty DataFrame on failure.
    """
    end_date = trade_date or _last_trading_day()
    # Go back 5 calendar days — covers weekends + holidays, guarantees 10-15 candles
    start_date = end_date - timedelta(days=5)

    end_str = end_date.strftime("%Y-%m-%d")
    start_str = start_date.strftime("%Y-%m-%d")

    # URL-encode the pipe character in instrument key
    encoded_key = instrument_key.replace("|", "%7C")
    # Upstox URL order is reversed: to_date (end) before from_date (start)
    url = f"{BASE_URL}/historical-candle/{encoded_key}/30minute/{end_str}/{start_str}"
    logger.info(f"Fetching candles URL: {url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=_get_headers())

        if response.status_code != 200:
            logger.warning(
                f"Upstox candles returned {response.status_code} for {instrument_key}"
            )
            return pd.DataFrame()

        data = response.json()
        candles = data.get("data", {}).get("candles", [])

        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume", "oi"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"Failed to fetch candles for {instrument_key}: {e}")
        return pd.DataFrame()


def calculate_vwap(df: pd.DataFrame) -> float:
    """Calculate VWAP from OHLCV data. Returns 0.0 on failure."""
    try:
        if df.empty or df["volume"].sum() == 0:
            return 0.0
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (typical_price * df["volume"]).sum() / df["volume"].sum()
        return round(float(vwap), 2)
    except Exception:
        return 0.0
