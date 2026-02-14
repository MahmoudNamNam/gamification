from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.db import get_users_collection, get_categories_collection
from app.core.errors import AppError, INVALID_CATEGORIES, USER_NOT_FOUND
from app.models.user import UserResponse, UpdateMeRequest, SetFavoriteCategoriesRequest
from app.services.auth_service import get_user_by_id
from app.utils.objectid import to_objectid
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter(tags=["users"])


def _user_to_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user.get("name"),
        favorite_category_ids=[str(x) for x in user.get("favorite_category_ids", [])],
        stats=user.get("stats", {}),
        entitlements=user.get("entitlements", {}),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    return _user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    req: UpdateMeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    users = get_users_collection()
    update = {}
    if req.name is not None:
        update["name"] = req.name
    if req.favorite_category_ids is not None:
        try:
            update["favorite_category_ids"] = [to_objectid(x) for x in req.favorite_category_ids]
        except Exception:
            pass
    if update:
        update["updated_at"] = datetime.now(timezone.utc)
        users.update_one({"_id": current_user["_id"]}, {"$set": update})
    user = users.find_one({"_id": current_user["_id"]})
    return _user_to_response(user)


@router.put("/me/favorite-categories", response_model=UserResponse)
def set_favorite_categories(
    req: SetFavoriteCategoriesRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Set the current user's favorite categories. Replaces the previous list. Only active categories are allowed."""
    if not req.category_ids:
        users = get_users_collection()
        users.update_one(
            {"_id": current_user["_id"]},
            {"$set": {"favorite_category_ids": [], "updated_at": datetime.now(timezone.utc)}},
        )
        user = users.find_one({"_id": current_user["_id"]})
        return _user_to_response(user)
    cats_col = get_categories_collection()
    valid_ids = []
    for cid in req.category_ids:
        if not ObjectId.is_valid(cid):
            raise AppError(INVALID_CATEGORIES, "Invalid category id", status_code=400, details={"category_id": cid})
        oid = ObjectId(cid)
        cat = cats_col.find_one({"_id": oid, "active": True})
        if not cat:
            raise AppError(INVALID_CATEGORIES, "Category not found or inactive", status_code=400, details={"category_id": cid})
        valid_ids.append(oid)
    users = get_users_collection()
    users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"favorite_category_ids": valid_ids, "updated_at": datetime.now(timezone.utc)}},
    )
    user = users.find_one({"_id": current_user["_id"]})
    return _user_to_response(user)


# --- Users CRUD (list, get by id, update, delete). Create = POST /register ---

@router.get("/users", response_model=list[UserResponse])
def list_users(
    current_user: Annotated[dict, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all users (authenticated)."""
    users_col = get_users_collection()
    cursor = users_col.find().skip(skip).limit(limit)
    return [_user_to_response(d) for d in cursor]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a user by id."""
    if not ObjectId.is_valid(user_id):
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    user = get_user_by_id(user_id)
    if not user:
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    return _user_to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    req: UpdateMeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a user by id (name and/or favorite_category_ids)."""
    if not ObjectId.is_valid(user_id):
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    users_col = get_users_collection()
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    update = {}
    if req.name is not None:
        update["name"] = req.name
    if req.favorite_category_ids is not None:
        try:
            update["favorite_category_ids"] = [to_objectid(x) for x in req.favorite_category_ids]
        except Exception:
            pass
    if update:
        update["updated_at"] = datetime.now(timezone.utc)
        users_col.update_one({"_id": ObjectId(user_id)}, {"$set": update})
    user = users_col.find_one({"_id": ObjectId(user_id)})
    return _user_to_response(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a user by id."""
    if not ObjectId.is_valid(user_id):
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    users_col = get_users_collection()
    result = users_col.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    return None
