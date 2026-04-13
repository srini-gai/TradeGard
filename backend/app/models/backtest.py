from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String
from app.database import Base
from app.models.base import TimestampMixin


class BacktestRun(Base, TimestampMixin):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(DateTime, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_signals = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    avg_pnl = Column(Float, nullable=False)
    best_trade_pnl = Column(Float, nullable=True)
    worst_trade_pnl = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    monthly_breakdown = Column(JSON, nullable=True)


class BacktestTrade(Base, TimestampMixin):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(5), nullable=False)
    entry_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=True)
    entry_premium = Column(Float, nullable=False)
    exit_premium = Column(Float, nullable=True)
    outcome = Column(String(10), nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
