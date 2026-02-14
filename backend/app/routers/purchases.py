from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from bson import ObjectId

from app.core.db import get_purchases_collection
from app.core.deps import get_current_user
from app.core.errors import AppError, PURCHASE_NOT_FOUND, FORBIDDEN
from app.models.purchase import PurchaseResponse

router = APIRouter(prefix="/purchases", tags=["purchases"])


def _doc_to_response(d: dict) -> PurchaseResponse:
    return PurchaseResponse(
        id=str(d["_id"]),
        user_id=str(d["user_id"]),
        product_id=str(d["product_id"]) if d.get("product_id") else None,
        provider=d.get("provider"),
        provider_ref=d.get("provider_ref"),
        rounds_delta=d.get("rounds_delta", 0),
        subscription_expires_at=d.get("subscription_expires_at"),
        created_at=d.get("created_at"),
    )


@router.get("", response_model=list[PurchaseResponse])
def list_purchases(
    current_user: Annotated[dict, Depends(get_current_user)],
    user_id: Optional[str] = Query(None, description="Filter by user (omit for current user only)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    col = get_purchases_collection()
    uid = str(current_user["_id"])
    # Only allow listing own purchases unless explicitly passing own user_id
    filter_user_id = user_id if user_id else uid
    if filter_user_id != uid:
        raise AppError(FORBIDDEN, "Cannot list another user's purchases", status_code=403)
    cursor = col.find({"user_id": ObjectId(filter_user_id)}).sort("created_at", -1).skip(skip).limit(limit)
    return [_doc_to_response(d) for d in cursor]


@router.get("/{purchase_id}", response_model=PurchaseResponse)
def get_purchase(
    purchase_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_purchases_collection()
    if not ObjectId.is_valid(purchase_id):
        raise AppError(PURCHASE_NOT_FOUND, "Purchase not found", status_code=404)
    doc = col.find_one({"_id": ObjectId(purchase_id)})
    if not doc:
        raise AppError(PURCHASE_NOT_FOUND, "Purchase not found", status_code=404)
    if str(doc["user_id"]) != str(current_user["_id"]):
        raise AppError(FORBIDDEN, "Cannot access another user's purchase", status_code=403)
    return _doc_to_response(doc)


@router.delete("/{purchase_id}", status_code=204)
def delete_purchase(
    purchase_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    col = get_purchases_collection()
    if not ObjectId.is_valid(purchase_id):
        raise AppError(PURCHASE_NOT_FOUND, "Purchase not found", status_code=404)
    doc = col.find_one({"_id": ObjectId(purchase_id)})
    if not doc:
        raise AppError(PURCHASE_NOT_FOUND, "Purchase not found", status_code=404)
    if str(doc["user_id"]) != str(current_user["_id"]):
        raise AppError(FORBIDDEN, "Cannot delete another user's purchase", status_code=403)
    col.delete_one({"_id": ObjectId(purchase_id)})
    return None
