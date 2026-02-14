from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from app.core.config import settings

_client: MongoClient | None = None
_db: Database | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGODB_URI)
    return _client


def get_db() -> Database:
    global _db
    if _db is None:
        _db = get_client()[settings.MONGODB_DB_NAME]
    return _db


def get_users_collection() -> Collection:
    return get_db()["users"]


def get_categories_collection() -> Collection:
    return get_db()["categories"]


def get_questions_collection() -> Collection:
    return get_db()["questions"]


def get_matches_collection() -> Collection:
    return get_db()["matches"]


def get_products_collection() -> Collection:
    return get_db()["products"]


def get_purchases_collection() -> Collection:
    return get_db()["purchases"]


def get_otps_collection() -> Collection:
    return get_db()["otps"]


def init_db() -> None:
    db = get_db()
    users = db["users"]
    users.create_index("email", unique=True)
    questions = db["questions"]
    questions.create_index([("category_id", 1), ("status", 1), ("level", 1)])
    matches = db["matches"]
    matches.create_index([("created_by_user_id", 1), ("status", 1)])
    purchases = db["purchases"]
    purchases.create_index([("user_id", 1), ("created_at", -1)])
    otps = db["otps"]
    otps.create_index([("email", 1), ("purpose", 1)])
    otps.create_index("expires_at", expireAfterSeconds=0)
