from pydantic_settings import BaseSettings
from typing import List


def _parse_cors_origins(value: str) -> List[str]:
    value = value.strip()
    if not value:
        return []
    if value == "*":
        return ["*"]
    return [origin.strip() for origin in value.split(",") if origin.strip()]


class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "khaleeji"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    # Environment: set to "development" for dev OTP (1–6 only, no email/SMS)
    ENV: str = "production"
    # OTP
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 6
    RETURN_OTP_IN_RESPONSE: bool = False  # Set True in dev to return OTP in request-otp response
    # SMTP (leave SMTP_HOST empty to skip sending OTP email and use stub/log only)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "خليجي"
    SMTP_USE_TLS: bool = True
    # Env as plain string (e.g. "*" or "http://localhost:3000,http://localhost:8000")
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return _parse_cors_origins(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
