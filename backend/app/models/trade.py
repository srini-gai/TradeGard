from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin


class Trade(Base, TimestampMixin):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(5), nullable=False)
    strike = Column(Float, nullable=False)
    expiry = Column(Date, nullable=False)
    entry_date = Column(DateTime, nullable=False)
    entry_premium = Column(Float, nullable=False)
    lots = Column(Integer, nullable=False)
    lot_size = Column(Integer, nullable=False)
    sl_premium = Column(Float, nullable=False)
    t1_premium = Column(Float, nullable=False)
    t2_premium = Column(Float, nullable=False)
    t3_premium = Column(Float, nullable=False)
    status = Column(String(20), default="OPEN")
    exit_premium = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)
    notes = Column(String(500), nullable=True)

    bookings = relationship(
        "PartialBooking", back_populates="trade", cascade="all, delete-orphan"
    )


class PartialBooking(Base, TimestampMixin):
    __tablename__ = "partial_bookings"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    level = Column(String(5), nullable=False)
    booked_at = Column(DateTime, nullable=False)
    qty_booked = Column(Integer, nullable=False)
    exit_premium = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)

    trade = relationship("Trade", back_populates="bookings")
