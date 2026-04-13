"""
Nifty 500 constituent symbols — fetched from official NSE CSV.
Cached locally at data/nifty500_cache.json.
Refresh by calling: refresh_nifty500_cache()
"""
import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Official NSE Nifty 500 CSV URL
NSE_NIFTY500_URL = (
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
)

# Local cache file path — lives next to this file
CACHE_FILE = Path(__file__).parent / "nifty500_cache.json"

# Cache TTL — 7 days
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# Known NSE symbol → yfinance symbol differences
YF_SYMBOL_MAP: dict[str, str] = {
    "M&M": "M&M.NS",
    "M&MFIN": "M&MFIN.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "L&TFH": "L&TFH.NS",
    "WAAREEENER": "WAAREEENER.NS",
    "MCX": "MCX.NS",
}

# Fallback — used if NSE fetch fails; verified yfinance symbols for ~100 liquid stocks
FALLBACK_SYMBOLS: list[str] = [
    # Nifty 50
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
    "BAJFINANCE", "WIPRO", "HCLTECH", "ULTRACEMCO", "NESTLEIND",
    "TECHM", "SUNPHARMA", "TATAMOTORS", "POWERGRID", "NTPC",
    "ONGC", "COALINDIA", "ADANIPORTS", "JSWSTEEL", "TATASTEEL",
    "BAJAJFINSV", "SBILIFE", "HDFCLIFE", "DRREDDY", "CIPLA",
    "DIVISLAB", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO", "BRITANNIA",
    "INDUSINDBK", "GRASIM", "TATACONSUM", "APOLLOHOSP", "BPCL",
    "LTIM", "HINDALCO", "VEDL", "SHRIRAMFIN", "ADANIENT",
    # Nifty Next 50 + popular mid-caps
    "DMART", "SIEMENS", "HAVELLS", "PIDILITIND", "DABUR",
    "MARICO", "BERGEPAINT", "GODREJCP", "MUTHOOTFIN", "LUPIN",
    "TORNTPHARM", "AUROPHARMA", "ALKEM", "BANKBARODA", "PNB",
    "CANBK", "UNIONBANK", "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK",
    "SAIL", "NMDC", "PETRONET", "IGL", "GAIL",
    "TATAPOWER", "ADANIGREEN", "IRCTC", "CONCOR", "ZOMATO",
    "IRFC", "PFC", "REC", "NHPC", "HAL",
    "BEL", "COCHINSHIP", "CHOLAFIN", "MPHASIS", "PERSISTENT",
    "COFORGE", "LTTS", "KPITTECH", "TATAELXSI", "OFSS",
    "MCX", "ANGELONE", "CDSL", "BSE", "CAMS",
    "OBEROIRLTY", "DLF", "GODREJPROP", "PRESTIGE", "BRIGADE",
    "JUBLFOOD", "DEVYANI", "ZYDUSLIFE", "IPCALAB", "GLENMARK",
    "LAURUS", "NATCOPHARM", "AJANTPHARM", "FORTIS", "MAXHEALTH",
    "VOLTAS", "BLUESTAR", "CROMPTON", "POLYCAB", "KEI",
    "SRF", "DEEPAKNTR", "NAVINFLUOR", "TATACHEM", "ATUL",
    "PAGEIND", "TRENT", "MANYAVAR", "BATA", "RELAXO",
    "INDHOTEL", "EIHOTEL", "PVRINOX", "SUNTV", "ZEEL",
    "INTERGLOBE", "BLUEDART", "ADANIENSOL", "TORNTPOWER", "CESC",
    "WAAREEENER", "SOLARINDS", "INDIGRID", "STLTECH",
    "AFFLE", "INFOEDGE", "INDIAMART", "MAPMYINDIA",
    "LATENTVIEW", "HAPPSTMNDS", "INTELLECT", "TANLA", "ROUTE",
    "M&M", "ASHOKLEY", "TVSMOTOR", "ESCORTS", "MOTHERSON",
    "BOSCHLTD", "ENDURANCE", "EXIDEIND", "YESBANK",
    "KARURVYSYA", "CITYUNIONBANK", "SOBHA", "KOLTEPATIL",
    "HDFCAMC", "NIPPONLIFE", "UTIAMC", "360ONE",
    "RAMCOCEM", "JKCEMENT", "DALMIA", "BIRLACORPN",
]


def _fetch_from_nse() -> list[str]:
    """
    Fetch official Nifty 500 list from NSE CSV.
    Returns plain NSE symbols (no .NS suffix).
    Raises on failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.niftyindices.com/",
    }

    # NSE requires a session cookie — warm up first
    session = requests.Session()
    session.get("https://www.niftyindices.com/", headers=headers, timeout=10)
    time.sleep(1)

    response = session.get(NSE_NIFTY500_URL, headers=headers, timeout=20)
    response.raise_for_status()

    lines = response.text.strip().split("\n")
    if len(lines) < 2:
        raise ValueError("NSE CSV response is unexpectedly short")

    header_cols = [h.strip().strip('"').strip("\r") for h in lines[0].split(",")]
    symbol_idx: int | None = None
    for i, h in enumerate(header_cols):
        if "symbol" in h.lower():
            symbol_idx = i
            break

    if symbol_idx is None:
        raise ValueError(f"No Symbol column found in NSE CSV. Headers: {header_cols}")

    symbols: list[str] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = [c.strip().strip('"').strip("\r") for c in line.split(",")]
        if len(cols) > symbol_idx:
            sym = cols[symbol_idx].strip()
            if sym:
                symbols.append(sym)

    logger.info(f"Fetched {len(symbols)} symbols from NSE official CSV")
    return symbols


def refresh_nifty500_cache() -> list[str]:
    """
    Force-refresh the Nifty 500 list from NSE and save to cache.
    Falls back to FALLBACK_SYMBOLS if NSE is unreachable.
    Returns the updated symbol list (plain NSE symbols, no .NS).
    """
    global _SYMBOLS_SET

    try:
        symbols = _fetch_from_nse()
        if len(symbols) < 400:
            raise ValueError(
                f"Too few symbols fetched: {len(symbols)} (expected ~500)"
            )

        cache_data = {
            "symbols": symbols,
            "fetched_at": time.time(),
            "count": len(symbols),
        }
        CACHE_FILE.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Nifty 500 cache updated — {len(symbols)} symbols")

    except Exception as e:
        logger.warning(f"NSE fetch failed: {e} — using fallback list")
        symbols = FALLBACK_SYMBOLS

    # Update in-memory set so is_valid_nifty500 reflects the new list immediately
    _SYMBOLS_SET = set(symbols)
    return symbols


def _load_from_cache() -> list[str] | None:
    """Load symbols from local cache if it exists and is not expired."""
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        age = time.time() - data.get("fetched_at", 0)
        if age > CACHE_TTL_SECONDS:
            logger.info("Nifty 500 cache expired — will refresh on next request")
            return None
        symbols = data.get("symbols", [])
        if len(symbols) < 400:
            return None
        logger.info(f"Loaded {len(symbols)} symbols from local cache")
        return symbols
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
        return None


def get_nifty500_symbols() -> list[str]:
    """
    Get Nifty 500 symbols as plain NSE names (no .NS suffix).
    Uses local cache if fresh, otherwise fetches from NSE.
    Falls back to hardcoded list if both fail.
    """
    cached = _load_from_cache()
    if cached:
        return cached
    return refresh_nifty500_cache()


def get_yf_symbol(nse_symbol: str) -> str:
    """Convert a plain NSE symbol to yfinance format (.NS suffix)."""
    sym = nse_symbol.upper().replace(".NS", "")
    return YF_SYMBOL_MAP.get(sym, f"{sym}.NS")


def get_nifty500_yf_symbols() -> list[str]:
    """Return symbols with .NS suffix for yfinance."""
    return [get_yf_symbol(s) for s in get_nifty500_symbols()]


# ── Module-level set for O(1) lookup ─────────────────────────────────────────
# Populated on import; updated by refresh_nifty500_cache() without restart.
try:
    _SYMBOLS_SET: set[str] = set(get_nifty500_symbols())
except Exception:
    _SYMBOLS_SET = set(FALLBACK_SYMBOLS)


def is_valid_nifty500(symbol: str) -> bool:
    """Return True if symbol is in the current Nifty 500 list."""
    sym = symbol.upper().replace(".NS", "")
    return sym in _SYMBOLS_SET


def get_nifty500_names() -> list[dict]:
    """Return sorted list of {symbol, label} dicts for frontend autocomplete."""
    seen: set[str] = set()
    result: list[dict] = []
    for s in sorted(_SYMBOLS_SET):
        if s not in seen:
            seen.add(s)
            result.append({"symbol": s, "label": s})
    return result


# Backward-compat alias used elsewhere in the codebase
NIFTY500_SYMBOLS = [get_yf_symbol(s) for s in sorted(_SYMBOLS_SET)]
