from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.errors import AppError, USER_EXISTS, INVALID_CREDENTIALS
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.db import get_db, get_users_collection
from app.models.user import (
    RegisterRequest,
    LoginRequest,
    UserEntitlements,
    UserStats,
    TokenResponse,
)


def get_users() -> Collection:
    return get_users_collection()


def register(req: RegisterRequest) -> TokenResponse:
    users = get_users()
    if users.find_one({"email": req.email}):
        raise AppError(USER_EXISTS, "Email already registered", status_code=409)
    now = datetime.now(timezone.utc)
    doc = {
        "email": req.email,
        "password_hash": get_password_hash(req.password),
        "name": req.name or None,
        "is_admin": False,
        "favorite_category_ids": [],
        "stats": UserStats().model_dump(),
        "entitlements": UserEntitlements().model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    r = users.insert_one(doc)
    user_id = str(r.inserted_id)
    return TokenResponse(access_token=create_access_token(user_id), token_type="bearer")


def login(req: LoginRequest) -> TokenResponse:
    users = get_users()
    user = users.find_one({"email": req.email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise AppError(INVALID_CREDENTIALS, "Invalid email or password", status_code=401)
    return TokenResponse(
        access_token=create_access_token(str(user["_id"])),
        token_type="bearer",
    )


def get_user_by_id(user_id: str) -> Optional[dict]:
    users = get_users()
    if not ObjectId.is_valid(user_id):
        return None
    return users.find_one({"_id": ObjectId(user_id)})


def forgot_password_stub(email: str) -> None:
    # Stub: in production would send OTP email
    pass
