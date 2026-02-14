from typing import Any, Optional


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# Common error codes
INVALID_CATEGORIES = "INVALID_CATEGORIES"
NO_ROUNDS_AVAILABLE = "NO_ROUNDS_AVAILABLE"
HINT_NOT_ALLOWED = "HINT_NOT_ALLOWED"
THROW_SOLO_MODE = "THROW_SOLO_MODE"
INVALID_ANSWER_KEYS = "INVALID_ANSWER_KEYS"
MATCH_NOT_FOUND = "MATCH_NOT_FOUND"
MATCH_NOT_ACTIVE = "MATCH_NOT_ACTIVE"
MATCH_ALREADY_FINISHED = "MATCH_ALREADY_FINISHED"
MAX_CATEGORIES_EXCEEDED = "MAX_CATEGORIES_EXCEEDED"
NO_QUESTIONS_LEFT_FOR_LEVEL = "NO_QUESTIONS_LEFT_FOR_LEVEL"
LEVEL_QUOTA_EXCEEDED = "LEVEL_QUOTA_EXCEEDED"
ROUND_ALREADY_JUDGED = "ROUND_ALREADY_JUDGED"
ROUND_NOT_FOUND = "ROUND_NOT_FOUND"
QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
PURCHASE_NOT_FOUND = "PURCHASE_NOT_FOUND"
USER_NOT_FOUND = "USER_NOT_FOUND"
UNAUTHORIZED = "UNAUTHORIZED"
USER_EXISTS = "USER_EXISTS"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
FORBIDDEN = "FORBIDDEN"
# OTP / email
EMAIL_SEND_FAILED = "EMAIL_SEND_FAILED"
INVALID_OTP = "INVALID_OTP"
OTP_EXPIRED = "OTP_EXPIRED"