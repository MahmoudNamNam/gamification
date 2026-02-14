from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.utils.objectid import PyObjectId


class UserStats(BaseModel):
    games_played: int = 0
    total_points: int = 0
    correct_answers: int = 0
    wrong_answers: int = 0


class SubscriptionInfo(BaseModel):
    active: bool = False
    plan_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class UserEntitlements(BaseModel):
    free_round_used: bool = False
    rounds_balance: int = 0
    subscription: SubscriptionInfo = SubscriptionInfo()


class UserInDB(BaseModel):
    id: Optional[PyObjectId] = None
    email: str
    password_hash: str
    name: Optional[str] = None
    is_admin: bool = False
    favorite_category_ids: list[PyObjectId] = []
    stats: UserStats = UserStats()
    entitlements: UserEntitlements = UserEntitlements()
    created_at: datetime = None
    updated_at: datetime = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    favorite_category_ids: list[str] = []
    stats: UserStats = UserStats()
    entitlements: UserEntitlements = UserEntitlements()

    class Config:
        from_attributes = True


class UpdateMeRequest(BaseModel):
    name: Optional[str] = None
    favorite_category_ids: Optional[list[str]] = None


class SetFavoriteCategoriesRequest(BaseModel):
    """Set the list of favorite category IDs (replaces previous list). Max 20."""
    category_ids: list[str] = Field(..., max_length=20, description="Category IDs to set as favorites")


class WalletResponse(BaseModel):
    free_round_used: bool
    rounds_balance: int
    subscription: SubscriptionInfo
