from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from bson import ObjectId

from app.core.db import get_products_collection
from app.core.deps import get_current_user
from app.core.errors import AppError, PRODUCT_NOT_FOUND
from app.models.product import ProductResponse, ProductCreate, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


def _doc_to_response(d: dict) -> ProductResponse:
    return ProductResponse(
        id=str(d["_id"]),
        name_ar=d["name_ar"],
        name_en=d["name_en"],
        type=d.get("type", "rounds"),
        rounds=d.get("rounds"),
        price_display=d.get("price_display"),
        active=d.get("active", True),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


@router.get("", response_model=list[ProductResponse])
def list_products(
    active_only: bool = Query(True, description="If true, return only active products"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    col = get_products_collection()
    q = {"active": True} if active_only else {}
    cursor = col.find(q).skip(skip).limit(limit)
    return [_doc_to_response(d) for d in cursor]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    col = get_products_collection()
    if not ObjectId.is_valid(product_id):
        raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
    doc = col.find_one({"_id": ObjectId(product_id)})
    if not doc:
        raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
    return _doc_to_response(doc)


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    data: ProductCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_products_collection()
    now = datetime.now(timezone.utc)
    doc = {
        "name_ar": data.name_ar,
        "name_en": data.name_en,
        "type": data.type,
        "rounds": data.rounds,
        "price_display": data.price_display,
        "active": data.active,
        "created_at": now,
        "updated_at": now,
    }
    r = col.insert_one(doc)
    doc["_id"] = r.inserted_id
    return _doc_to_response(doc)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    data: ProductUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_products_collection()
    if not ObjectId.is_valid(product_id):
        raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
    update = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if not update:
        doc = col.find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
        return _doc_to_response(doc)
    update["updated_at"] = datetime.now(timezone.utc)
    result = col.find_one_and_update(
        {"_id": ObjectId(product_id)},
        {"$set": update},
        return_document=True,
    )
    if not result:
        raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
    return _doc_to_response(result)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_products_collection()
    if not ObjectId.is_valid(product_id):
        raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
    result = col.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise AppError(PRODUCT_NOT_FOUND, "Product not found", status_code=404)
    return None
