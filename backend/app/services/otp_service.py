"""
OTP (One-Time Password) service.
- request_otp: generate, store, and "send" OTP (stub; in prod use email/SMS provider).
- verify_otp: validate OTP and perform action (login, register, forgot_password).
"""
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from pymongo.collection import Collection

from app.core.config import settings
from app.core.db import get_otps_collection, get_users_collection
from app.core.email import is_smtp_configured, send_otp_email
from app.core.errors import AppError, EMAIL_SEND_FAILED, INVALID_OTP, OTP_EXPIRED, USER_EXISTS, USER_NOT_FOUND
from app.core.security import get_password_hash, create_access_token
from app.models.user import UserEntitlements, UserStats, TokenResponse


def get_otps() -> Collection:
    return get_otps_collection()


def get_users() -> Collection:
    return get_users_collection()


OTP_PURPOSE = Literal["register", "login", "forgot_password"]


def _as_utc(dt: datetime) -> datetime:
    """Return datetime as timezone-aware UTC (MongoDB may return naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


DEV_OTP_DIGITS = ("1", "2", "3", "4", "5", "6")


def _is_dev_env() -> bool:
    return getattr(settings, "ENV", "production").lower() == "development"


def _generate_otp(length: int | None = None) -> str:
    if _is_dev_env():
        return random.choice(DEV_OTP_DIGITS)
    length = length or settings.OTP_LENGTH
    return "".join(random.choices(string.digits, k=length))


def _send_otp(email: str, otp: str, purpose: str) -> None:
    """Send OTP via SMTP if configured. In dev env we do not call any external service."""
    if _is_dev_env():
        return
    if is_smtp_configured():
        try:
            send_otp_email(email, otp, purpose)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Failed to send OTP email: %s", e)
            raise AppError(EMAIL_SEND_FAILED, "Could not send verification email", status_code=500)
    else:
        import logging
        logging.getLogger(__name__).info("OTP for %s (purpose=%s): %s", email, purpose, otp)


def request_otp(email: str, purpose: OTP_PURPOSE) -> dict:
    """
    Generate OTP, store with expiry, and send. Any existing OTP for this email+purpose is replaced.
    Returns dict with optional 'otp' key when RETURN_OTP_IN_RESPONSE is True (dev only).
    For registration use request_register_otp(email, password, name) instead.
    """
    if purpose == "register":
        if get_users().find_one({"email": email}):
            raise AppError(USER_EXISTS, "Email already registered", status_code=409)
    elif purpose in ("login", "forgot_password"):
        if not get_users().find_one({"email": email}):
            raise AppError(USER_NOT_FOUND, "No account with this email", status_code=404)

    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    col = get_otps()
    col.delete_many({"email": email.lower(), "purpose": purpose})
    col.insert_one({
        "email": email.lower(),
        "otp": otp,
        "purpose": purpose,
        "expires_at": expires_at,
        "created_at": now,
    })
    _send_otp(email, otp, purpose)

    out: dict = {"message": "OTP sent"}
    if settings.RETURN_OTP_IN_RESPONSE:
        out["otp"] = otp
    return out


def request_register_otp(email: str, password: str, name: Optional[str] = None) -> dict:
    """
    Register step 1: store email, password_hash, name with OTP and send OTP.
    User completes registration by calling verify_otp_register(email, otp) with the OTP received.
    """
    if get_users().find_one({"email": email.lower()}):
        raise AppError(USER_EXISTS, "Email already registered", status_code=409)
    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    col = get_otps()
    col.delete_many({"email": email.lower(), "purpose": "register"})
    col.insert_one({
        "email": email.lower(),
        "otp": otp,
        "purpose": "register",
        "password_hash": get_password_hash(password),
        "name": name or None,
        "expires_at": expires_at,
        "created_at": now,
    })
    _send_otp(email, otp, "register")
    out: dict = {"message": "OTP sent to your email. Enter it to complete registration."}
    if settings.RETURN_OTP_IN_RESPONSE:
        out["otp"] = otp
    return out


def _normalize_dev_otp(otp: str) -> Optional[str]:
    """In dev, OTP is one digit 1-6. Return that digit if input starts with one of them, else None."""
    s = (otp or "").strip()
    if s and s[0] in DEV_OTP_DIGITS:
        return s[0]
    return None


def _otp_matches(stored_otp: str, supplied_otp: str) -> bool:
    """True if supplied OTP is valid for the stored one. In dev, any digit 1-6 matches any 1-6."""
    if stored_otp == supplied_otp:
        return True
    if _is_dev_env() and stored_otp in DEV_OTP_DIGITS:
        normalized = _normalize_dev_otp(supplied_otp)
        return normalized is not None  # any 1-6 accepted in dev
    return False


def _find_valid_otp(email: str, otp: str, purpose: str) -> None:
    """Find and delete OTP if valid. Raises AppError if missing, expired, or wrong."""
    col = get_otps()
    doc = col.find_one({
        "email": email.lower(),
        "purpose": purpose,
    })
    if not doc:
        raise AppError(INVALID_OTP, "Invalid or expired OTP", status_code=400)
    expires_at = _as_utc(doc["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        col.delete_one({"_id": doc["_id"]})
        raise AppError(OTP_EXPIRED, "OTP has expired", status_code=400)
    if not _otp_matches(doc["otp"], otp):
        raise AppError(INVALID_OTP, "Invalid OTP", status_code=400)
    col.delete_one({"_id": doc["_id"]})


def verify_otp_login(email: str, otp: str) -> TokenResponse:
    """Verify OTP for login and return JWT."""
    _find_valid_otp(email, otp, "login")
    user = get_users().find_one({"email": email.lower()})
    if not user:
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    return TokenResponse(
        access_token=create_access_token(str(user["_id"])),
        token_type="bearer",
    )


def verify_otp_register(email: str, otp: str) -> TokenResponse:
    """
    Register step 2: verify OTP and create account using stored password/name from step 1.
    Returns JWT. Body: { "email", "otp" } only.
    """
    if get_users().find_one({"email": email.lower()}):
        raise AppError(USER_EXISTS, "Email already registered", status_code=409)
    col = get_otps()
    doc = col.find_one({"email": email.lower(), "purpose": "register"})
    if not doc:
        raise AppError(INVALID_OTP, "Invalid or expired OTP", status_code=400)
    expires_at = _as_utc(doc["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        col.delete_one({"_id": doc["_id"]})
        raise AppError(OTP_EXPIRED, "OTP has expired", status_code=400)
    if not _otp_matches(doc["otp"], otp):
        raise AppError(INVALID_OTP, "Invalid OTP", status_code=400)
    password_hash = doc["password_hash"]
    name = doc.get("name")
    col.delete_one({"_id": doc["_id"]})
    now = datetime.now(timezone.utc)
    user_doc = {
        "email": email.lower(),
        "password_hash": password_hash,
        "name": name,
        "is_admin": False,
        "favorite_category_ids": [],
        "stats": UserStats().model_dump(),
        "entitlements": UserEntitlements().model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    r = get_users().insert_one(user_doc)
    return TokenResponse(
        access_token=create_access_token(str(r.inserted_id)),
        token_type="bearer",
    )


def verify_otp_forgot_password(email: str, otp: str, new_password: str) -> TokenResponse:
    """Verify OTP for forgot password: set new password and return JWT."""
    _find_valid_otp(email, otp, "forgot_password")
    user = get_users().find_one({"email": email.lower()})
    if not user:
        raise AppError(USER_NOT_FOUND, "User not found", status_code=404)
    get_users().update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": get_password_hash(new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    return TokenResponse(
        access_token=create_access_token(str(user["_id"])),
        token_type="bearer",
    )
