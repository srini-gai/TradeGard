# Database Skill — SQLite + SQLAlchemy

> TradeGuard uses SQLite. No PostgreSQL, no Alembic, no Docker DB needed.
> Tables are auto-created on startup via `Base.metadata.create_all()`.

---

## Database Connection

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../database/tradeguard.db")
)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Auto-create all tables on startup. No migrations needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)
```

---

## Base Mixin

```python
# app/models/base.py
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class TimestampMixin:
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

---

## Signal Model

```python
# app/models/signal.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON
from app.database import Base
from app.models.base import TimestampMixin

class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_date = Column(Date, nullable=False, index=True)
    direction = Column(String(5), nullable=False)       # CE or PE
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
    rationale = Column(JSON, nullable=True)             # List of reason strings
```

---

## Trade Model

```python
# app/models/trade.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin

class Trade(Base, TimestampMixin):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(5), nullable=False)        # CE or PE
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
    status = Column(String(20), default="OPEN")          # OPEN/PARTIAL/CLOSED/SL_HIT
    exit_premium = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)
    notes = Column(String(500), nullable=True)

    bookings = relationship("PartialBooking", back_populates="trade", cascade="all, delete-orphan")


class PartialBooking(Base, TimestampMixin):
    __tablename__ = "partial_bookings"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    level = Column(String(5), nullable=False)            # T1/T2/T3/SL
    booked_at = Column(DateTime, nullable=False)
    qty_booked = Column(Integer, nullable=False)
    exit_premium = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)

    trade = relationship("Trade", back_populates="bookings")
```

---

## Backtest Models

```python
# app/models/backtest.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, ForeignKey
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
    outcome = Column(String(10), nullable=True)          # T1/T2/T3/SL/EXPIRED
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
```

---

## Alert Model

```python
# app/models/alert.py
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from app.database import Base
from app.models.base import TimestampMixin

class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    action = Column(String(20), nullable=False)          # BUY_CE / BUY_PE / EXIT
    price = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)
    payload = Column(JSON, nullable=True)                # Full raw webhook payload
    received_at = Column(DateTime, nullable=False)
    source = Column(String(50), default="tradingview")
```

---

## Query Patterns

```python
# Get today's signals
from datetime import date
signals = db.query(Signal).filter(Signal.signal_date == date.today()).all()

# Get open trades
open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()

# Count today's trades (for risk rule enforcement)
from datetime import datetime
today_start = datetime.combine(date.today(), datetime.min.time())
today_count = db.query(Trade).filter(Trade.entry_date >= today_start).count()

# Get latest backtest run
latest = db.query(BacktestRun).order_by(BacktestRun.run_date.desc()).first()
```

---

## Startup Init

```python
# Call this in main.py on startup
from app.database import init_db

@app.on_event("startup")
async def startup():
    init_db()  # Creates all tables if they don't exist
```

---

## Best Practices for This Project

- Never use Alembic — `init_db()` handles everything
- Always use `check_same_thread=False` for SQLite with FastAPI
- Store dates as `Date` type, datetimes as `DateTime`
- Store JSON data (rationale, payloads) as `JSON` column type
- Index columns used in filters: symbol, signal_date, status
- Use `cascade="all, delete-orphan"` on child relationships
