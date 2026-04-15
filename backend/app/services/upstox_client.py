import logging
from calendar import monthrange
from datetime import date, timedelta

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.upstox.com/v2"

# ISIN mapping for Nifty 50 stocks (NSE symbol → ISIN)
# Instrument key format: NSE_EQ|{ISIN}
NIFTY50_ISIN: dict[str, str] = {
    "RELIANCE":   "INE002A01018",
    "TCS":        "INE467B01029",
    "HDFCBANK":   "INE040A01034",
    "INFY":       "INE009A01021",
    "ICICIBANK":  "INE090A01021",
    "HINDUNILVR": "INE030A01027",
    "SBIN":       "INE062A01020",
    "BHARTIARTL": "INE397D01024",
    "ITC":        "INE154A01025",
    "KOTAKBANK":  "INE237A01028",
    "LT":         "INE018A01030",
    "HCLTECH":    "INE860A01027",
    "AXISBANK":   "INE238A01034",
    "BAJFINANCE": "INE296A01024",
    "ASIANPAINT": "INE021A01026",
    "MARUTI":     "INE585B01010",
    "SUNPHARMA":  "INE044A01036",
    "TITAN":      "INE280A01028",
    "ULTRACEMCO": "INE481G01011",
    "ONGC":       "INE213A01029",
    "WIPRO":      "INE075A01022",
    "NTPC":       "INE733E01010",
    "POWERGRID":  "INE752E01010",
    "NESTLEIND":  "INE239A01016",
    "TECHM":      "INE669C01036",
    "M&M":        "INE101A01026",
    "TATASTEEL":  "INE081A01012",
    "JSWSTEEL":   "INE019A01038",
    "ADANIENT":   "INE423A01024",
    "ADANIPORTS":  "INE742F01042",
    "COALINDIA":  "INE522F01014",
    "BAJAJFINSV": "INE918I01026",
    "DIVISLAB":   "INE361B01024",
    "DRREDDY":    "INE089A01031",
    "EICHERMOT":  "INE066A01013",
    "GRASIM":     "INE047A01021",
    "HEROMOTOCO": "INE158A01026",
    "HINDALCO":   "INE038A01020",
    "INDUSINDBK": "INE095A01012",
    "CIPLA":      "INE059A01026",
    "SBILIFE":    "INE330C01018",
    "HDFCLIFE":   "INE795G01014",
    "TATACONSUM": "INE192A01025",
    "TATAMOTORS": "INE155A01022",
    "BAJAJ-AUTO": "INE917I01010",
    "APOLLOHOSP": "INE437A01024",
    "BPCL":       "INE029A01011",
    "BRITANNIA":  "INE216A01030",
    "SHRIRAMFIN": "INE721A01013",
    "TRENT":      "INE849A01020",
    # Mid-cap / Nifty 500 additions
    "SIEMENS":    "INE003A01024",
    "DIXON":      "INE935N01020",
    "MPHASIS":    "INE356A01018",
    "PERSISTENT": "INE262H01021",
    "COFORGE":    "INE591G01017",
    "LTTS":       "INE010V01017",
    "KPITTECH":   "INE218J01022",
    "TATAELXSI":  "INE670A01012",
    "HAL":        "INE066F01020",
    "BEL":        "INE263A01024",
    "COCHINSHIP": "INE704P01017",
    "IRCTC":      "INE335Y01020",
    "CDSL":       "INE736A01011",
    "BSE":        "INE118H01025",
    "ANGELONE":   "INE906B01023",
    "ZOMATO":     "INE758T01015",
    "DMART":      "INE192R01011",
    "NAUKRI":     "INE663F01024",
    "INDIAMART":  "INE116L01010",
    "AFFLE":      "INE00WC01019",
    "HAVELLS":    "INE176B01034",
    "VOLTAS":     "INE226A01021",
    "POLYCAB":    "INE455K01017",
    "PAGEIND":    "INE761H01022",
    "JUBLFOOD":   "INE797F01020",
}


# NSE holiday-adjusted expiry overrides.
# When the last Thursday of a month is an NSE holiday, expiry moves to the
# previous trading day. Update this dict after each NSE holiday announcement.
# Format: "YYYY-MM" -> "YYYY-MM-DD"
NSE_EXPIRY_OVERRIDES: dict[str, str] = {
    "2026-04": "2026-04-28",  # Apr 30 = Akshaya Tritiya (NSE holiday)
}


def get_monthly_expiry(for_date: date | None = None) -> str:
    """
    Return the monthly options expiry date as YYYY-MM-DD.

    Base rule: last Thursday of the month.
    Holiday override: if NSE_EXPIRY_OVERRIDES has an entry for that month,
    use that date instead (NSE moves expiry when last Thursday is a holiday).

    If today is past that expiry, roll to next month.
    """
    ref = for_date or date.today()
    year, month = ref.year, ref.month

    def _last_thursday(y: int, m: int) -> date:
        last_day = monthrange(y, m)[1]
        for day in range(last_day, 0, -1):
            if date(y, m, day).weekday() == 3:
                return date(y, m, day)
        return date(y, m, 1)  # fallback (shouldn't happen)

    def _expiry_for_month(y: int, m: int) -> date:
        key = f"{y}-{m:02d}"
        if key in NSE_EXPIRY_OVERRIDES:
            return date.fromisoformat(NSE_EXPIRY_OVERRIDES[key])
        return _last_thursday(y, m)

    expiry = _expiry_for_month(year, month)

    # If today is past this month's expiry, roll to next month
    if ref > expiry:
        month += 1
        if month > 12:
            month = 1
            year += 1
        expiry = _expiry_for_month(year, month)

    return expiry.isoformat()


def get_instrument_key(symbol: str) -> str:
    """
    Return the Upstox instrument key for a Nifty 50 stock.
    Format: NSE_EQ|{ISIN}
    Falls back to NSE_EQ|{symbol} if ISIN not found (for unknown symbols).
    """
    sym = symbol.upper().replace(".NS", "")
    isin = NIFTY50_ISIN.get(sym)
    if isin:
        return f"NSE_EQ|{isin}"
    logger.warning(f"ISIN not found for {sym} — using symbol fallback")
    return f"NSE_EQ|{sym}"


def _parse_options_chain(raw: dict, symbol: str) -> dict:
    """
    Parse Upstox v2 options chain response into a clean structure.

    Upstox v2 response shape:
    {
      "status": "success",
      "data": [
        {
          "expiry": "2026-04-28",
          "strike_price": 1280.0,
          "call_options": {
            "instrument_key": "NSE_FO|...",
            "market_data": {
              "ltp": 45.5,
              "volume": 12345,
              "oi": 56789,
              "bid_price": 45.0,
              "ask_price": 46.0,
              "prev_close": 40.0,
              "iv": 18.5
            },
            "option_greeks": { "delta": 0.52, "theta": -0.8, "vega": 2.1, "gamma": 0.005 }
          },
          "put_options": { ... same shape ... }
        },
        ...
      ]
    }
    """
    if not raw or raw.get("status") != "success":
        return {"symbol": symbol, "error": "No data from Upstox", "strikes": []}

    data = raw.get("data", [])
    if not data:
        return {"symbol": symbol, "error": "Empty options chain", "strikes": []}

    # Determine ATM strike by finding the row with smallest |CE delta - 0.5|
    # or smallest |strike - current_price| if greeks aren't available
    strikes_parsed = []
    atm_strike = None
    atm_ce_ltp = None
    atm_pe_ltp = None
    best_atm_score = float("inf")

    for row in data:
        strike = row.get("strike_price", 0)
        ce = row.get("call_options", {})
        pe = row.get("put_options", {})
        ce_md = ce.get("market_data", {}) or {}
        pe_md = pe.get("market_data", {}) or {}
        ce_greeks = ce.get("option_greeks", {}) or {}
        pe_greeks = pe.get("option_greeks", {}) or {}

        ce_ltp = ce_md.get("ltp", 0) or 0
        pe_ltp = pe_md.get("ltp", 0) or 0
        ce_iv = ce_md.get("iv", 0) or 0
        pe_iv = pe_md.get("iv", 0) or 0
        ce_delta = ce_greeks.get("delta", 0) or 0
        pe_delta = pe_greeks.get("delta", 0) or 0
        ce_oi = ce_md.get("oi", 0) or 0
        pe_oi = pe_md.get("oi", 0) or 0

        entry = {
            "strike": strike,
            "ce": {
                "ltp": ce_ltp,
                "iv": ce_iv,
                "oi": ce_oi,
                "volume": ce_md.get("volume", 0) or 0,
                "delta": ce_delta,
                "theta": ce_greeks.get("theta", 0) or 0,
                "vega": ce_greeks.get("vega", 0) or 0,
            },
            "pe": {
                "ltp": pe_ltp,
                "iv": pe_iv,
                "oi": pe_oi,
                "volume": pe_md.get("volume", 0) or 0,
                "delta": pe_delta,
                "theta": pe_greeks.get("theta", 0) or 0,
                "vega": pe_greeks.get("vega", 0) or 0,
            },
        }
        strikes_parsed.append(entry)

        # ATM = strike where CE delta closest to 0.5
        if ce_delta:
            score = abs(ce_delta - 0.5)
        else:
            # Fallback: parity where CE ≈ PE premium
            score = abs(ce_ltp - pe_ltp) if (ce_ltp and pe_ltp) else float("inf")

        if score < best_atm_score:
            best_atm_score = score
            atm_strike = strike
            atm_ce_ltp = ce_ltp
            atm_pe_ltp = pe_ltp

    # Sort by strike ascending
    strikes_parsed.sort(key=lambda x: x["strike"])

    expiry = data[0].get("expiry", "") if data else ""

    return {
        "symbol": symbol,
        "expiry": expiry,
        "atm_strike": atm_strike,
        "atm_ce_ltp": atm_ce_ltp,
        "atm_pe_ltp": atm_pe_ltp,
        "strikes": strikes_parsed,
    }


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.upstox_access_token}",
        "Accept": "application/json",
    }


async def get_options_chain(symbol: str, expiry: str | None = None) -> dict | None:
    """
    Fetch live options chain for a symbol from Upstox v2.

    symbol: NSE symbol e.g. 'RELIANCE'
    expiry: date string e.g. '2026-04-28' — defaults to current monthly expiry
    """
    sym_upper = symbol.upper().replace(".NS", "")
    instrument_key = get_instrument_key(sym_upper)
    expiry_date = expiry or get_monthly_expiry()

    logger.info(
        f"Fetching options chain: symbol={sym_upper}, "
        f"instrument_key={instrument_key}, expiry={expiry_date}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/option/chain",
                params={
                    "instrument_key": instrument_key,
                    "expiry_date": expiry_date,
                },
                headers=get_headers(),
            )

        if response.status_code == 200:
            raw = response.json()
            return _parse_options_chain(raw, sym_upper)

        logger.warning(
            f"Upstox options chain returned {response.status_code} for {sym_upper}: "
            f"{response.text[:200]}"
        )
        return None

    except Exception as e:
        logger.error(f"Upstox API error for {sym_upper}: {e}")
        return None


async def get_market_quote(symbol: str) -> dict | None:
    """Fetch live market quote for a symbol."""
    sym_upper = symbol.upper().replace(".NS", "")
    instrument_key = get_instrument_key(sym_upper)

    try:
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
        logger.error(f"Upstox quote error for {sym_upper}: {e}")
        return None


def get_options_chain_sync(symbol: str, expiry: str | None = None) -> dict | None:
    """
    Synchronous wrapper around get_options_chain.
    Safe to call from sync FastAPI routes (which run in a thread pool with no
    active event loop). Do NOT call from inside a running async event loop.
    """
    import asyncio
    try:
        return asyncio.run(get_options_chain(symbol, expiry))
    except Exception as e:
        logger.error(f"Sync options chain fetch failed for {symbol}: {e}")
        return None


def is_upstox_configured() -> bool:
    """Check if Upstox API credentials are set."""
    return bool(settings.upstox_access_token and settings.upstox_api_key)
