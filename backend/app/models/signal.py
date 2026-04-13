from sqlalchemy import Column, Date, Float, Integer, JSON, String
from app.database import Base
from app.models.base import TimestampMixin


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_date = Column(Date, nullable=False, index=True)
    direction = Column(String(5), nullable=False)
    strike = Column(Float, nullable=False)
    expiry = Column(Date, nullable=False)
    entry_premium = Column(Float, nullable=False)
    sl_premium = Column(Float, nullable=False)
    t1_premium = Column(Float, nullable=False)
    t2_premium = Column(Float, nullable=False)
    t3_premium = Column(Float, nullable=False)
    t1_date = Column(Date, nullable=True)
    t2_date = Column(Date, nullable=True)
    t3_date = Column(Date, nullable=True)
    confidence_score = Column(Integer, nullable=False)
    rationale = Column(JSON, nullable=True)
