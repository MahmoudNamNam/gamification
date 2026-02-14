from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.utils.objectid import PyObjectId


class Product(BaseModel):
    id: Optional[PyObjectId] = None
    name_ar: str
    name_en: str
    type: Literal["rounds", "subscription"] = "rounds"
    rounds: Optional[int] = None  # for rounds pack
    price_display: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class ProductCreate(BaseModel):
    name_ar: str
    name_en: str
    type: Literal["rounds", "subscription"] = "rounds"
    rounds: Optional[int] = None
    price_display: Optional[str] = None
    active: bool = True


class ProductUpdate(BaseModel):
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    type: Optional[Literal["rounds", "subscription"]] = None
    rounds: Optional[int] = None
    price_display: Optional[str] = None
    active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    name_ar: str
    name_en: str
    type: str
    rounds: Optional[int] = None
    price_display: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
