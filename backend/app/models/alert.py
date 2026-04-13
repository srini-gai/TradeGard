from sqlalchemy import Column, DateTime, Float, Integer, JSON, String
from app.database import Base
from app.models.base import TimestampMixin


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    action = Column(String(20), nullable=False)
    price = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)
    payload = Column(JSON, nullable=True)
    received_at = Column(DateTime, nullable=False)
    source = Column(String(50), default="tradingview")
