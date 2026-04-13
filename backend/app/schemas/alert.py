from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class AlertResponse(BaseModel):
    id: int
    symbol: str
    action: str
    price: Optional[float] = None
    rsi: Optional[float] = None
    payload: Optional[Any] = None
    received_at: datetime
    source: str

    model_config = {"from_attributes": True}
