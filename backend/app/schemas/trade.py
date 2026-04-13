from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PartialBookingCreate(BaseModel):
    level: str
    booked_at: datetime
    qty_booked: int
    exit_premium: float

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        if v not in ("T1", "T2", "T3", "SL"):
            raise ValueError("level must be T1, T2, T3, or SL")
        return v


class PartialBookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: int
    level: str
    booked_at: datetime
    qty_booked: int
    exit_premium: float
    pnl: float


class TradeCreate(BaseModel):
    symbol: str
    direction: str
    strike: float
    expiry: date
    entry_premium: float
    lots: int
    lot_size: int = 0
    sl_premium: float
    t1_premium: float
    t2_premium: float
    t3_premium: float
    notes: Optional[str] = None
    signal_id: Optional[int] = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("CE", "PE"):
            raise ValueError("direction must be CE or PE")
        return v

    @field_validator("lots")
    @classmethod
    def validate_lots(cls, v: int) -> int:
        if v < 1:
            raise ValueError("lots must be at least 1")
        return v

    @field_validator("sl_premium")
    @classmethod
    def validate_sl(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("SL premium is required and must be > 0")
        return v


class TradeUpdate(BaseModel):
    status: Optional[str] = None
    exit_premium: Optional[float] = None
    total_pnl: Optional[float] = None
    notes: Optional[str] = None


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    direction: str
    strike: float
    expiry: date
    entry_date: datetime
    entry_premium: float
    lots: int
    lot_size: int
    sl_premium: float
    t1_premium: float
    t2_premium: float
    t3_premium: float
    status: str
    exit_premium: Optional[float] = None
    total_pnl: Optional[float] = None
    notes: Optional[str] = None
    signal_id: Optional[int] = None
    bookings: list[PartialBookingResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class BookingRequest(BaseModel):
    level: str
    exit_premium: float

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        if v not in ("T1", "T2", "T3", "SL"):
            raise ValueError("level must be T1, T2, T3, or SL")
        return v


class JournalSummary(BaseModel):
    period: str
    total_trades: int
    open_trades: int
    closed_trades: int
    sl_hit: int
    win_rate: float
    total_pnl: float
    best_trade_pnl: Optional[float] = None
    worst_trade_pnl: Optional[float] = None
