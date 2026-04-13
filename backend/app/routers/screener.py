import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.signal import Signal
from app.schemas.signal import SignalResponse, ScreenerRunResponse
from app.services.screener_service import run_screener as _run
from app.services.screener_service import save_signals
from data.nifty500 import (
    is_valid_nifty500,
    get_nifty500_names,
    get_yf_symbol,
    refresh_nifty500_cache,
)

router = APIRouter(prefix="/api/screener", tags=["screener"])
logger = logging.getLogger(__name__)


@router.post("/run", response_model=ScreenerRunResponse)
def run_screener_now(db: Session = Depends(get_db)):
    """
    Manually trigger the screener. Runs synchronously and returns signals.
    Also persists results to DB.
    """
    logger.info("Manual screener run triggered")
    try:
        signals = _run()
        save_signals(signals, db)
        return ScreenerRunResponse(
            status="complete",
            signals_found=len(signals),
            signals=signals,
            run_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Screener run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Screener failed: {str(e)}") from e


@router.get("/signals/today")
def get_today_signals(db: Session = Depends(get_db)):
    """Return signals generated today."""
    today = date.today()
    signals = (
        db.query(Signal)
        .filter(Signal.signal_date == today)
        .order_by(Signal.confidence_score.desc())
        .all()
    )
    return {
        "date": today.isoformat(),
        "count": len(signals),
        "signals": [SignalResponse.model_validate(s).model_dump() for s in signals],
    }


@router.get("/signals")
def get_all_signals(
    limit: int = 20,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """Return all past signals paginated."""
    signals = (
        db.query(Signal)
        .order_by(Signal.signal_date.desc(), Signal.confidence_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    total = db.query(Signal).count()
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "signals": [SignalResponse.model_validate(s).model_dump() for s in signals],
    }


@router.get("/signals/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Return a single signal by ID."""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.get("/nifty500")
def get_nifty500():
    """Return full Nifty 500 symbol list for frontend autocomplete."""
    names = get_nifty500_names()
    return {"symbols": names, "count": len(names)}


@router.post("/nifty500/refresh")
def refresh_nifty500():
    """
    Force-refresh Nifty 500 list from NSE official CSV.
    Call this after NSE quarterly rebalancing.
    Falls back to hardcoded list if NSE is unreachable.
    """
    symbols = refresh_nifty500_cache()
    return {
        "status": "refreshed",
        "count": len(symbols),
        "message": f"Nifty 500 list updated with {len(symbols)} symbols from NSE",
    }


@router.get("/analyse/{symbol}")
def analyse_symbol(symbol: str):
    """
    Run screener analysis on any Nifty 500 stock on-demand.
    Returns signal dict with score, confidence, T1/T2/T3 — same as screener output.
    Does NOT save to the signals DB (on-demand analysis only).
    """
    sym_upper = symbol.upper().replace(".NS", "")
    yf_symbol = get_yf_symbol(sym_upper)

    if not is_valid_nifty500(sym_upper):
        raise HTTPException(
            status_code=404,
            detail=(
                f"{sym_upper} is not in the current Nifty 500 list. "
                "If this is a new addition, call POST /api/screener/nifty500/refresh "
                "to update the list from NSE."
            ),
        )

    logger.info(f"On-demand analysis for {sym_upper}")

    try:
        from app.core.screener import score_symbol
        result = score_symbol(yf_symbol)

        if result is not None:
            return {
                "qualified": True,
                "symbol": sym_upper,
                "current_price": result.get("current_price"),
                "rsi": result.get("rsi"),
                "ema20": result.get("ema20"),
                "volume_ratio": result.get("volume_ratio"),
                "above_ema": (result.get("current_price", 0) or 0) > (result.get("ema20", 0) or 0),
                "confidence_score": result["confidence_score"],
                "reason": "Qualifies — all filters passed",
                "signal": result,
            }

        # Stock didn't qualify — fetch raw indicators to explain why
        from app.services.data_fetcher import fetch_historical
        from app.core.indicators import (
            calculate_rsi,
            calculate_ema,
            calculate_volume_ratio,
        )

        df = fetch_historical(yf_symbol, days=90)
        if df.empty:
            raise HTTPException(
                status_code=503,
                detail=f"Could not fetch data for {sym_upper} from yfinance",
            )

        close = df["Close"].astype(float)
        volume = df["Volume"].astype(float)
        rsi = calculate_rsi(close)
        ema20 = calculate_ema(close)
        vol_ratio = calculate_volume_ratio(volume)
        current_price = round(float(close.iloc[-1]), 2)
        above_ema = current_price > ema20

        reason = "Stock did not pass all screener filters (RSI not in signal zone or score below threshold)"
        if rsi >= 0:
            if above_ema and not (55 <= rsi <= 70):
                reason = f"RSI {rsi} not in bullish zone (55–70) for CE signal"
            elif not above_ema and not (30 <= rsi <= 45):
                reason = f"RSI {rsi} not in bearish zone (30–45) for PE signal"

        return {
            "qualified": False,
            "symbol": sym_upper,
            "current_price": current_price,
            "rsi": rsi if rsi >= 0 else None,
            "ema20": ema20 if ema20 >= 0 else None,
            "volume_ratio": round(vol_ratio, 2),
            "above_ema": above_ema,
            "confidence_score": 0,
            "reason": reason,
            "signal": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {sym_upper}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
