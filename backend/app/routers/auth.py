from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field, model_validator
from app.models.user import LoginRequest, TokenResponse
from app.services.auth_service import login
from app.services.otp_service import (
    request_otp as otp_request_otp,
    request_register_otp,
    verify_otp_login,
    verify_otp_register,
    verify_otp_forgot_password,
)
from app.core.errors import AppError, USER_NOT_FOUND

router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    """Register: full name, email, password. OTP sent to email; complete with POST /auth/verify-otp/register (email + otp)."""
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=1)


# --- OTP ---

class RequestOtpRequest(BaseModel):
    email: EmailStr
    purpose: Literal["register", "login", "forgot_password"]


class VerifyOtpLoginRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=1, max_length=8)


class VerifyOtpRegisterRequest(BaseModel):
    """Complete registration: enter OTP received by email. Returns token."""
    email: EmailStr
    otp: str = Field(..., min_length=1, max_length=8)


class VerifyOtpForgotPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=1, max_length=8)
    new_password: str = Field(..., min_length=1)
    new_password_confirm: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError("Passwords do not match")
        return self


@router.post("/register")
def auth_register(req: RegisterRequest):
    """Submit full name, email, password. OTP is sent to email. User then calls POST /auth/verify-otp/register with email + otp to complete and get token."""
    return request_register_otp(req.email, req.password, req.name)


@router.post("/login", response_model=TokenResponse)
def auth_login(req: LoginRequest):
    return login(req)


@router.post("/forgot-password")
def auth_forgot_password(req: ForgotPasswordRequest):
    """Request password reset: sends OTP to email. Then use POST /auth/verify-otp/forgot-password with email, otp, new_password, new_password_confirm."""
    try:
        otp_request_otp(req.email, "forgot_password")
    except AppError as e:
        if e.code == USER_NOT_FOUND:
            # Same response to avoid email enumeration
            pass
        else:
            raise
    return {"message": "If an account exists for this email, a verification code has been sent."}


@router.post("/request-otp")
def auth_request_otp(req: RequestOtpRequest):
    """Send OTP to email for register, login, or forgot_password. Set RETURN_OTP_IN_RESPONSE=true in dev to get OTP in response."""
    return otp_request_otp(req.email, req.purpose)


@router.post("/verify-otp/login", response_model=TokenResponse)
def auth_verify_otp_login(req: VerifyOtpLoginRequest):
    """Verify OTP and return JWT (passwordless login)."""
    return verify_otp_login(req.email, req.otp)


@router.post("/verify-otp/register", response_model=TokenResponse)
def auth_verify_otp_register(req: VerifyOtpRegisterRequest):
    """Enter OTP received by email to complete registration; returns JWT."""
    return verify_otp_register(req.email, req.otp)


@router.post("/verify-otp/forgot-password", response_model=TokenResponse)
def auth_verify_otp_forgot_password(req: VerifyOtpForgotPasswordRequest):
    """Verify OTP and set new password; returns JWT."""
    return verify_otp_forgot_password(req.email, req.otp, req.new_password)
