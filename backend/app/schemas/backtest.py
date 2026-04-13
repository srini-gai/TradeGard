from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class BacktestTradeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    symbol: str
    direction: str
    entry_date: str
    exit_date: Optional[str] = None
    entry_premium: float
    exit_premium: Optional[float] = None
    outcome: str
    pnl: Optional[float] = None
    pnl_pct: float


class BacktestRunResponse(BaseModel):
    id: Optional[int] = None
    run_date: Optional[str] = None
    period_start: str
    period_end: str
    total_signals: int
    win_rate: float
    avg_pnl: float
    best_trade_pnl: Optional[float] = None
    worst_trade_pnl: Optional[float] = None
    max_drawdown: Optional[float] = None
    monthly_breakdown: dict[str, Any]
    status: str = "complete"


class BacktestSummaryResponse(BaseModel):
    has_results: bool
    summary: Optional[BacktestRunResponse] = None
    message: str = ""
