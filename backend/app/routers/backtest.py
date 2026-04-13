import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.backtest import BacktestRun
from app.schemas.backtest import BacktestRunResponse, BacktestSummaryResponse
from app.services.backtest_service import (
    get_backtest_summary,
    get_backtest_trades,
    run_and_save_backtest,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = logging.getLogger(__name__)

_backtest_running = False


@router.post("/run")
def run_backtest_endpoint(months: int = 3, db: Session = Depends(get_db)):
    """
    Run a full backtest for the last N months.
    WARNING: Takes several minutes — pre-fetches data for all 50 stocks.
    months: 1–6 (default 3)
    """
    global _backtest_running
    if _backtest_running:
        raise HTTPException(
            status_code=409,
            detail="A backtest is already running — please wait",
        )
    if months < 1 or months > 6:
        raise HTTPException(status_code=400, detail="months must be between 1 and 6")

    _backtest_running = True
    try:
        result = run_and_save_backtest(months=months, db=db)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return {
            "status": "complete",
            "db_id": result.get("db_id"),
            "period_start": result["period_start"],
            "period_end": result["period_end"],
            "total_signals": result["total_signals"],
            "win_rate": result["win_rate"],
            "avg_pnl": result["avg_pnl"],
            "best_trade_pnl": result["best_trade_pnl"],
            "worst_trade_pnl": result["worst_trade_pnl"],
            "max_drawdown": result["max_drawdown"],
            "monthly_breakdown": result["monthly_breakdown"],
            "trades_count": len(result.get("trades", [])),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Backtest failed: {str(e)}"
        ) from e
    finally:
        _backtest_running = False


@router.get("/results")
def get_all_runs(limit: int = 10, db: Session = Depends(get_db)):
    """Return list of all past backtest runs (summary only)."""
    runs = (
        db.query(BacktestRun)
        .order_by(BacktestRun.run_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "run_date": r.run_date.isoformat(),
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "total_signals": r.total_signals,
            "win_rate": r.win_rate,
            "avg_pnl": r.avg_pnl,
            "max_drawdown": r.max_drawdown,
        }
        for r in runs
    ]


@router.get("/results/{run_id}")
def get_run_detail(run_id: int, db: Session = Depends(get_db)):
    """Return a specific backtest run with all individual trades."""
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    trades = get_backtest_trades(run_id, db)
    return {
        "id": run.id,
        "run_date": run.run_date.isoformat(),
        "period_start": run.period_start.isoformat(),
        "period_end": run.period_end.isoformat(),
        "total_signals": run.total_signals,
        "win_rate": run.win_rate,
        "avg_pnl": run.avg_pnl,
        "best_trade_pnl": run.best_trade_pnl,
        "worst_trade_pnl": run.worst_trade_pnl,
        "max_drawdown": run.max_drawdown,
        "monthly_breakdown": run.monthly_breakdown,
        "trades": trades,
    }


@router.get("/summary", response_model=BacktestSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    """Return the most recent backtest run summary."""
    summary = get_backtest_summary(db)
    if not summary:
        return BacktestSummaryResponse(
            has_results=False,
            message="No backtest runs yet — POST /api/backtest/run to start",
        )
    s = dict(summary)
    if s.get("monthly_breakdown") is None:
        s["monthly_breakdown"] = {}
    return BacktestSummaryResponse(
        has_results=True,
        summary=BacktestRunResponse.model_validate(s),
    )
