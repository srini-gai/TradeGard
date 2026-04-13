import logging

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.upstox.com/v2"


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.upstox_access_token}",
        "Accept": "application/json",
    }


async def get_options_chain(symbol: str, expiry: str) -> dict | None:
    """
    Fetch live options chain for a symbol from Upstox.
    symbol: NSE symbol e.g. 'RELIANCE'
    expiry: date string e.g. '2026-04-24'
    """
    try:
        instrument_key = f"NSE_EQ|{symbol}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/option/chain",
                params={
                    "instrument_key": instrument_key,
                    "expiry_date": expiry,
                },
                headers=get_headers(),
            )
        if response.status_code == 200:
            return response.json()
        logger.warning(
            f"Upstox options chain returned {response.status_code} for {symbol}"
        )
        return None
    except Exception as e:
        logger.error(f"Upstox API error for {symbol}: {e}")
        return None


async def get_market_quote(symbol: str) -> dict | None:
    """Fetch live market quote for a symbol."""
    try:
        instrument_key = f"NSE_EQ|{symbol}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/market-quote/quotes",
                params={"instrument_key": instrument_key},
                headers=get_headers(),
            )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Upstox quote error for {symbol}: {e}")
        return None


def is_upstox_configured() -> bool:
    """Check if Upstox API credentials are set."""
    return bool(settings.upstox_access_token and settings.upstox_api_key)
