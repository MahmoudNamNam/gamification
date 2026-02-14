from typing import Optional

from pydantic import BaseModel, Field

from app.utils.objectid import PyObjectId


class Category(BaseModel):
    id: Optional[PyObjectId] = None
    name_ar: str
    name_en: str
    icon_url: Optional[str] = None
    active: bool = True
    order: int = 0

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class CategoryCreate(BaseModel):
    name_ar: str
    name_en: str
    icon_url: Optional[str] = None
    active: bool = True
    order: int = 0


class CategoryUpdate(BaseModel):
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    icon_url: Optional[str] = None
    active: Optional[bool] = None
    order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: str
    name_ar: str
    name_en: str
    icon_url: Optional[str] = None
    active: bool = True
    order: int = 0
