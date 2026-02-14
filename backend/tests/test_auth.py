import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@patch("app.core.config.settings.RETURN_OTP_IN_RESPONSE", True)
def test_register_and_login():
    email = f"test_auth_{uuid.uuid4().hex[:12]}@example.com"
    password = "secret123"
    name = "Test User"
    # Step 1: register with name, email, password -> OTP sent
    r = client.post("/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "otp" in data
    otp = data["otp"]
    # Step 2: enter OTP to complete registration -> token
    r2 = client.post("/auth/verify-otp/register", json={"email": email, "otp": otp})
    assert r2.status_code == 200
    assert "access_token" in r2.json()

    r3 = client.post("/auth/login", json={"email": email, "password": password})
    assert r3.status_code == 200
    assert "access_token" in r3.json()


def test_login_invalid_credentials():
    r = client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "wrong"})
    assert r.status_code == 401
    assert "error" in r.json()


@patch("app.core.config.settings.RETURN_OTP_IN_RESPONSE", True)
def test_register_duplicate_email():
    email = f"dup_{uuid.uuid4().hex[:12]}@example.com"
    # First registration: register then enter OTP to complete
    client.post("/auth/register", json={"name": "User A", "email": email, "password": "pass"})
    r_otp = client.post("/auth/register", json={"name": "User A", "email": email, "password": "pass"})
    assert r_otp.status_code == 200
    otp = r_otp.json()["otp"]
    client.post("/auth/verify-otp/register", json={"email": email, "otp": otp})
    # Second registration attempt (email already exists) -> 409
    r = client.post("/auth/register", json={"name": "User B", "email": email, "password": "pass2"})
    assert r.status_code == 409
