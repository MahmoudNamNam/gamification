from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.utils.objectid import PyObjectId


class Purchase(BaseModel):
    id: Optional[PyObjectId] = None
    user_id: PyObjectId
    product_id: Optional[PyObjectId] = None
    provider: Optional[str] = None
    provider_ref: Optional[str] = None
    rounds_delta: int = 0  # +5, -1, etc.
    subscription_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True


class PurchaseResponse(BaseModel):
    id: str
    user_id: str
    product_id: Optional[str] = None
    provider: Optional[str] = None
    provider_ref: Optional[str] = None
    rounds_delta: int = 0
    subscription_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class RoundPackPurchaseRequest(BaseModel):
    product_id: Optional[str] = None  # stub
    rounds: int = 5  # stub: how many rounds to add
