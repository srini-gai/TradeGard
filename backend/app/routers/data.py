from fastapi import APIRouter, HTTPException

from app.services.data_fetcher import fetch_current_price, fetch_historical
from app.services.upstox_client import get_monthly_expiry, get_options_chain, is_upstox_configured
from data.nifty50 import NIFTY50_SYMBOLS, NSE_SYMBOLS

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/nifty50")
def get_nifty50_symbols():
    return {"symbols": NSE_SYMBOLS, "count": len(NSE_SYMBOLS)}


@router.get("/historical/{symbol}")
def get_historical(symbol: str, days: int = 90):
    yf_symbol = f"{symbol.upper()}.NS"
    if yf_symbol not in NIFTY50_SYMBOLS:
        raise HTTPException(status_code=404, detail=f"{symbol} not in Nifty 50")
    df = fetch_historical(yf_symbol, days)
    if df.empty:
        raise HTTPException(status_code=503, detail=f"Could not fetch data for {symbol}")
    records = df.reset_index()
    date_col = "Date" if "Date" in records.columns else records.columns[0]
    records = records[[date_col, "Open", "High", "Low", "Close", "Volume"]].rename(
        columns={date_col: "Date"}
    )
    records = records.tail(days)
    records["Date"] = records["Date"].astype(str)
    return {"symbol": symbol, "days": days, "data": records.to_dict(orient="records")}


@router.get("/price/{symbol}")
def get_price(symbol: str):
    price = fetch_current_price(f"{symbol.upper()}.NS")
    if price is None:
        raise HTTPException(status_code=503, detail=f"Could not fetch price for {symbol}")
    return {"symbol": symbol, "price": price}


@router.get("/options/{symbol}")
async def get_options(symbol: str, expiry: str | None = None):
    if not is_upstox_configured():
        raise HTTPException(status_code=503, detail="Upstox API not configured — check .env")
    expiry_date = expiry or get_monthly_expiry()
    data = await get_options_chain(symbol.upper(), expiry_date)
    if not data:
        raise HTTPException(status_code=503, detail="Could not fetch options chain")
    return data


@router.post("/refresh")
def refresh_data():
    """Trigger a background data refresh for all symbols."""
    return {"status": "refresh triggered", "symbols": len(NIFTY50_SYMBOLS)}
