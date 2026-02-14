from typing import Annotated, Literal

from fastapi import Depends, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.errors import AppError, UNAUTHORIZED, FORBIDDEN
from app.core.security import decode_access_token
from app.services.auth_service import get_user_by_id

security = HTTPBearer(auto_error=False)


def get_preferred_lang(
    accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
    lang: Annotated[str | None, Query(description="Preferred language: ar or en")] = None,
) -> Literal["ar", "en"]:
    """Resolve preferred language from query param ?lang= or Accept-Language header. Default: en."""
    if lang and lang in ("ar", "en"):
        return lang
    if accept_language:
        # e.g. "ar", "ar-SA", "en-US,en;q=0.9,ar;q=0.8"
        for part in accept_language.split(","):
            part = part.split(";")[0].strip().lower()
            if part.startswith("ar"):
                return "ar"
            if part.startswith("en"):
                return "en"
    return "en"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    if not credentials:
        raise AppError(UNAUTHORIZED, "Not authenticated", status_code=401)
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise AppError(UNAUTHORIZED, "Invalid or expired token", status_code=401)
    user = get_user_by_id(user_id)
    if not user:
        raise AppError(UNAUTHORIZED, "User not found", status_code=401)
    return user


def get_current_admin_user(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Require the current user to have is_admin=True. Use for admin-only routes."""
    if not current_user.get("is_admin"):
        raise AppError(FORBIDDEN, "Admin access required", status_code=403)
    return current_user
