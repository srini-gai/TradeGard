from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "tradeguard.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
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
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    from app.models import signal, trade, backtest, alert  # noqa: F401  (imports IntradaySignal too)

    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialised at {DB_PATH}")
