from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SignalBase(BaseModel):
    symbol: str
    direction: str
    strike: float
    expiry: date
    entry_premium: float
    sl_premium: float
    t1_premium: float
    t2_premium: float
    t3_premium: float
    t1_date: Optional[date] = None
    t2_date: Optional[date] = None
    t3_date: Optional[date] = None
    confidence_score: int
    rationale: Optional[list[str]] = None


class SignalResponse(SignalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signal_date: date
    created_at: Optional[datetime] = None


class ScreenerRunResponse(BaseModel):
    status: str
    signals_found: int
    signals: list[dict]
    run_at: str
