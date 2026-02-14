from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from bson import ObjectId

from app.core.db import get_categories_collection
from app.core.deps import get_current_user
from app.core.errors import AppError, CATEGORY_NOT_FOUND
from app.models.category import CategoryResponse, CategoryCreate, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _doc_to_response(d: dict) -> CategoryResponse:
    return CategoryResponse(
        id=str(d["_id"]),
        name_ar=d["name_ar"],
        name_en=d["name_en"],
        icon_url=d.get("icon_url"),
        active=d.get("active", True),
        order=d.get("order", 0),
    )


@router.get("", response_model=list[CategoryResponse])
def list_categories(active_only: bool = Query(True, description="If true, return only active categories")):
    col = get_categories_collection()
    q = {"active": True} if active_only else {}
    cursor = col.find(q).sort("order", 1)
    return [_doc_to_response(d) for d in cursor]


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: str):
    col = get_categories_collection()
    if not ObjectId.is_valid(category_id):
        raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
    doc = col.find_one({"_id": ObjectId(category_id)})
    if not doc:
        raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
    return _doc_to_response(doc)


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_categories_collection()
    now = datetime.now(timezone.utc)
    doc = {
        "name_ar": data.name_ar,
        "name_en": data.name_en,
        "icon_url": data.icon_url,
        "active": data.active,
        "order": data.order,
        "created_at": now,
        "updated_at": now,
    }
    r = col.insert_one(doc)
    doc["_id"] = r.inserted_id
    return _doc_to_response(doc)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_categories_collection()
    if not ObjectId.is_valid(category_id):
        raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
    update = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if not update:
        doc = col.find_one({"_id": ObjectId(category_id)})
        if not doc:
            raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
        return _doc_to_response(doc)
    update["updated_at"] = datetime.now(timezone.utc)
    result = col.find_one_and_update(
        {"_id": ObjectId(category_id)},
        {"$set": update},
        return_document=True,
    )
    if not result:
        raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
    return _doc_to_response(result)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_categories_collection()
    if not ObjectId.is_valid(category_id):
        raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
    result = col.delete_one({"_id": ObjectId(category_id)})
    if result.deleted_count == 0:
        raise AppError(CATEGORY_NOT_FOUND, "Category not found", status_code=404)
    return None
