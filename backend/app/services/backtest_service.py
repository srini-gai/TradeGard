import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.backtester import run_backtest as _run_backtest
from app.database import SessionLocal
from app.models.backtest import BacktestRun, BacktestTrade

logger = logging.getLogger(__name__)


def run_and_save_backtest(months: int = 3, db: Session | None = None) -> dict:
    """
    Run backtest and persist results to DB.
    Returns the result dict with added db_id field.
    """
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        logger.info(f"Starting backtest for {months} months")
        result = _run_backtest(months=months)

        if "error" in result:
            logger.warning(f"Backtest returned no trades: {result['error']}")
            return result

        run = BacktestRun(
            run_date=datetime.now(),
            period_start=date.fromisoformat(result["period_start"]),
            period_end=date.fromisoformat(result["period_end"]),
            total_signals=result["total_signals"],
            win_rate=result["win_rate"],
            avg_pnl=result["avg_pnl"],
            best_trade_pnl=result["best_trade_pnl"],
            worst_trade_pnl=result["worst_trade_pnl"],
            max_drawdown=result["max_drawdown"],
            monthly_breakdown=result["monthly_breakdown"],
        )
        db.add(run)
        db.flush()

        for t in result["trades"]:
            bt = BacktestTrade(
                backtest_run_id=run.id,
                symbol=t["symbol"],
                direction=t["direction"],
                entry_date=date.fromisoformat(t["entry_date"]),
                exit_date=date.fromisoformat(t["exit_date"])
                if t.get("exit_date")
                else None,
                entry_premium=t["entry_premium"],
                exit_premium=t.get("exit_premium"),
                outcome=t["outcome"],
                pnl=t.get("pnl_abs"),
                pnl_pct=t["pnl_pct"],
            )
            db.add(bt)

        db.commit()
        db.refresh(run)

        result["db_id"] = run.id
        logger.info(
            f"Backtest saved — run_id={run.id}, trades={len(result['trades'])}"
        )
        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Backtest save failed: {e}")
        raise
    finally:
        if own_db:
            db.close()


def get_backtest_summary(db: Session) -> dict | None:
    """Return the most recent BacktestRun summary."""
    run = db.query(BacktestRun).order_by(BacktestRun.run_date.desc()).first()
    if not run:
        return None
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
    }


def get_backtest_trades(run_id: int, db: Session) -> list[dict]:
    """Return all trades for a given backtest run."""
    trades = (
        db.query(BacktestTrade)
        .filter(BacktestTrade.backtest_run_id == run_id)
        .order_by(BacktestTrade.entry_date)
        .all()
    )
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "entry_date": t.entry_date.isoformat(),
            "exit_date": t.exit_date.isoformat() if t.exit_date else None,
            "entry_premium": t.entry_premium,
            "exit_premium": t.exit_premium,
            "outcome": t.outcome,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
        }
        for t in trades
    ]
