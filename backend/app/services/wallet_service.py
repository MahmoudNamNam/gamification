from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo.collection import Collection

from app.core.db import get_users_collection, get_purchases_collection
from app.core.errors import AppError, NO_ROUNDS_AVAILABLE
from app.models.user import UserEntitlements, WalletResponse, SubscriptionInfo


def get_users() -> Collection:
    return get_users_collection()


def get_purchases() -> Collection:
    return get_purchases_collection()


def get_wallet(user_id: str) -> WalletResponse:
    users = get_users()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return WalletResponse(
            free_round_used=True,
            rounds_balance=0,
            subscription=SubscriptionInfo(),
        )
    ent = user.get("entitlements", {})
    sub = ent.get("subscription", {})
    return WalletResponse(
        free_round_used=ent.get("free_round_used", True),
        rounds_balance=ent.get("rounds_balance", 0),
        subscription=SubscriptionInfo(
            active=sub.get("active", False),
            plan_id=sub.get("plan_id"),
            expires_at=sub.get("expires_at"),
        ),
    )


def consume_round(user_id: str) -> None:
    """Decrement rounds_balance by 1. Call only when not using free round."""
    users = get_users()
    result = users.update_one(
        {"_id": ObjectId(user_id), "entitlements.rounds_balance": {"$gt": 0}},
        {"$inc": {"entitlements.rounds_balance": -1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count == 0:
        raise AppError(NO_ROUNDS_AVAILABLE, "No rounds available", status_code=403)


def use_free_round(user_id: str) -> None:
    """Mark free_round_used = True."""
    users = get_users()
    users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "entitlements.free_round_used": True,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


def can_start_match(user_id: str) -> tuple[bool, bool]:
    """
    Returns (can_start, used_free_round).
    can_start: True if user has free round or rounds_balance > 0.
    used_free_round: True if we will consume the free round (not a paid round).
    """
    users = get_users()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return False, False
    ent = user.get("entitlements", {})
    free_used = ent.get("free_round_used", True)
    balance = ent.get("rounds_balance", 0)
    if not free_used:
        return True, True  # will use free round
    if balance > 0:
        return True, False  # will consume 1 round
    return False, False


def add_rounds(user_id: str, delta: int, product_id: Optional[str] = None, provider: Optional[str] = None, provider_ref: Optional[str] = None) -> None:
    """Add rounds to user balance and record purchase."""
    users = get_users()
    purchases = get_purchases()
    now = datetime.now(timezone.utc)
    users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$inc": {"entitlements.rounds_balance": delta},
            "$set": {"updated_at": now},
        },
    )
    purchases.insert_one({
        "user_id": ObjectId(user_id),
        "product_id": ObjectId(product_id) if product_id and ObjectId.is_valid(product_id) else None,
        "provider": provider,
        "provider_ref": provider_ref,
        "rounds_delta": delta,
        "subscription_expires_at": None,
        "created_at": now,
    })
