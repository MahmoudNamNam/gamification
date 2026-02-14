"""
Create or promote an admin user by email.

Usage:
  python -m scripts.create_admin admin@example.com
  python -m scripts.create_admin admin@example.com mypassword

If the user exists, they are promoted to admin (is_admin=True).
If not, a new user is created with the given email and password (default: password123).

Run from backend dir. Ensure MONGODB_URI is set (e.g. in .env or export).
"""
import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import get_db, init_db
from app.core.security import get_password_hash
from app.models.user import UserStats, UserEntitlements


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.create_admin <email> [password]")
        print("  email: required")
        print("  password: optional, default 'password123' (used only when creating a new user)")
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    password = sys.argv[2].strip() if len(sys.argv) > 2 else "password123"

    init_db()
    db = get_db()
    users = db["users"]

    existing = users.find_one({"email": email})
    if existing:
        if existing.get("is_admin"):
            print(f"User {email} is already an admin.")
            return
        users.update_one(
            {"email": email},
            {"$set": {"is_admin": True, "updated_at": datetime.now(timezone.utc)}},
        )
        print(f"Promoted {email} to admin.")
        return

    now = datetime.now(timezone.utc)
    doc = {
        "email": email,
        "password_hash": get_password_hash(password),
        "name": None,
        "is_admin": True,
        "favorite_category_ids": [],
        "stats": UserStats().model_dump(),
        "entitlements": UserEntitlements().model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    users.insert_one(doc)
    print(f"Created admin user {email} (password: {password}).")


if __name__ == "__main__":
    main()
