"""
Seed script: creates dummy data in all collections.
- categories (16 challenge fields)
- questions (per category: 4 per level 1/2/3 for first 6 categories, 4 per level for rest; Gulf-themed Arabic prompts)
- users (dummy accounts, password: password123)
- products (rounds packs, subscription)
- matches (team mode, new progress/rounds shape)
- purchases (user purchases)

Run from backend dir: python -m scripts.seed
Ensure MONGODB_URI is set (e.g. in .env or export).
To re-seed questions (e.g. after adding more), clear the questions collection first or use a fresh DB.
If you get NO_QUESTIONS_LEFT_FOR_LEVEL for a category, run: python -m scripts.ensure_min_questions
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from bson import ObjectId

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import get_db, init_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import UserStats, UserEntitlements


def prompt_block(text: str | None = None, url: str | None = None) -> dict:
    return {
        "text": text,
        "media": {"kind": "url", "url": url, "gridfs_file_id": None, "base64": None, "mime": None} if url else None,
    }


# Challenge fields from "Choose challenge fields" UI (اختر ميادين التحدي)
CHALLENGE_CATEGORIES = [
    ("الرياضة", "Sports"),
    ("السينما", "Cinema"),
    ("الدين والثقافة", "Religion and Culture"),
    ("الفنون", "Arts"),
    ("الجغرافيا", "Geography"),
    ("العلوم", "Science"),
    ("تاريخ الخليج", "Gulf History"),
    ("الطعام والمأكولات", "Food and Cuisine"),
    ("الثقافة والتراث", "Culture and Heritage"),
    ("الصحة", "Health"),
    ("الأدب العربي", "Arabic Literature"),
    ("التكنولوجيا", "Technology"),
    ("الاقتصاد", "Economy"),
    ("المناسبات والأعياد", "Events and Holidays"),
    ("الشخصيات", "Personalities"),
    ("الموسيقى الخليجية", "Gulf Music"),
]


def seed_categories(db):
    col = db["categories"]
    existing = col.count_documents({})
    if existing >= 16:
        print(f"Categories already have {existing} documents, skipping insert.")
        return list(col.find().sort("order", 1).limit(20))
    categories = []
    for i, (name_ar, name_en) in enumerate(CHALLENGE_CATEGORIES, start=1):
        categories.append({
            "_id": ObjectId(),
            "name_ar": name_ar,
            "name_en": name_en,
            "icon_url": None,
            "active": True,
            "order": i,
        })
    col.insert_many(categories)
    print(f"Inserted {len(categories)} categories.")
    return list(col.find().sort("order", 1))


# Pool of dummy questions by level (Arabic prompt only). Game needs at least 2 per category per level.
LEVEL_1_PROMPTS = [
    "ما عاصمة دولة الإمارات؟",
    "ما هي عاصمة المملكة العربية السعودية؟",
    "ما عاصمة الكويت؟",
    "ما عاصمة قطر؟",
    "ما عاصمة البحرين؟",
    "ما عاصمة سلطنة عمان؟",
    "كم عدد دول الخليج العربي؟",
    "ما اسم أطول برج في العالم؟",
    "في أي قارة تقع دول الخليج؟",
    "ما العملة الرسمية في السعودية؟",
]
LEVEL_2_PROMPTS = [
    "في أي عام تأسست دولة الإمارات؟",
    "كم عدد دول مجلس التعاون الخليجي؟",
    "ما هو العام الذي تأسس فيه مجلس التعاون؟",
    "ما اسم أول رئيس لدولة الإمارات؟",
    "ما هي أكبر دولة خليجية من حيث المساحة؟",
    "في أي عام تم توحيد المملكة العربية السعودية؟",
    "ما اسم المضيق الذي يربط الخليج بالمحيط؟",
    "ما هي اللغة الرسمية في دول الخليج؟",
    "ما اسم أشهر سوق في دبي؟",
    "ما هي عاصمة الثقافة العربية لإحدى السنوات؟",
]
LEVEL_3_PROMPTS = [
    "من كان أول حاكم لإمارة دبي من آل مكتوم؟",
    "في أي عام تم توحيد المملكة العربية السعودية؟",
    "ما اسم المعاهدة التي أنهت الحماية البريطانية على الخليج؟",
    "من أسس دولة قطر الحديثة؟",
    "ما اسم أقدم جامعة في الخليج؟",
    "في أي عام اكتشف النفط في البحرين؟",
    "ما اسم الشاعر الخليجي صاحب ديوان «الرعاة»؟",
    "ما هي أول دولة خليجية أصدرت عملة ورقية؟",
    "من هو مؤسس دولة الكويت الحديثة؟",
    "ما اسم المعرض العالمي الذي استضافته دبي؟",
]
# Generic prompts for categories 7–16 (varied)
EXTRA_PROMPTS = [
    "سؤال تجريبي في هذا المجال.",
    "ما الذي يميز هذا المجال في الخليج؟",
    "اذكر مثالاً مشهوراً من هذا المجال.",
    "ما أبرز إنجاز في هذا المجال؟",
    "كيف يرتبط هذا المجال بثقافة الخليج؟",
    "ما أشهر شخصية في هذا المجال؟",
]


def _add_question(questions: list, cid, level: int, points: int, prompt_text: str, hint_text: str | None = None, answer_text: str | None = None, now=None):
    q = {
        "_id": ObjectId(),
        "category_id": cid,
        "level": level,
        "points": points,
        "prompt": prompt_block(prompt_text),
        "hint": {"enabled": bool(hint_text), "content": prompt_block(hint_text) if hint_text else None},
        "answer": prompt_block(answer_text) if answer_text else None,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    questions.append(q)


def seed_questions(db, category_ids):
    col = db["questions"]
    if col.count_documents({}) > 0:
        print("Questions already exist, skipping.")
        return
    now = datetime.now(timezone.utc)
    questions = []
    # First 6 categories: 4 questions per level (so plenty for multiple matches)
    ANSWER_1 = "أبوظبي"
    ANSWER_2 = "1971"
    ANSWER_3 = "الشيخ راشد بن سعيد آل مكتوم"
    EXTRA_ANSWER = "إجابة تجريبية."
    for idx, cid in enumerate(category_ids[:6]):
        for i in range(4):
            _add_question(questions, cid, 1, 100, LEVEL_1_PROMPTS[(idx * 4 + i) % len(LEVEL_1_PROMPTS)], None, ANSWER_1, now)
        for i in range(4):
            _add_question(questions, cid, 2, 200, LEVEL_2_PROMPTS[(idx * 4 + i) % len(LEVEL_2_PROMPTS)], None, ANSWER_2, now)
        for i in range(4):
            hint = "تلميح: فكّر في التاريخ أو الجغرافيا." if i >= 2 else None
            _add_question(questions, cid, 3, 500, LEVEL_3_PROMPTS[(idx * 4 + i) % len(LEVEL_3_PROMPTS)], hint, ANSWER_3, now)
    # Remaining 10 categories: 4 questions per level with varied prompts
    for idx, cid in enumerate(category_ids[6:]):
        for level, points in [(1, 100), (2, 200), (3, 500)]:
            for i in range(4):
                prompt = EXTRA_PROMPTS[(idx * 3 + level + i) % len(EXTRA_PROMPTS)]
                hint = "تلميح عام." if level == 3 and i >= 2 else None
                _add_question(questions, cid, level, points, prompt, hint, EXTRA_ANSWER, now)
    col.insert_many(questions)
    print(f"Inserted {len(questions)} questions.")


DUMMY_PASSWORD = "password123"


def seed_users(db):
    col = db["users"]
    if col.count_documents({}) > 0:
        print("Users already exist, skipping.")
        return list(col.find())
    now = datetime.now(timezone.utc)
    pwd_hash = get_password_hash(DUMMY_PASSWORD)
    users_data = [
        {"email": "ahmed@example.com", "name": "أحمد", "is_admin": False},
        {"email": "sara@example.com", "name": "سارة", "is_admin": False},
        {"email": "omar@example.com", "name": "عمر", "is_admin": False},
        {"email": "nora@example.com", "name": "نورا", "is_admin": False},
        {"email": "demo@example.com", "name": "Demo User", "is_admin": True},
        {"email": "admin@example.com", "name": "Admin", "is_admin": True},
    ]
    docs = []
    for u in users_data:
        doc = {
            "_id": ObjectId(),
            "email": u["email"],
            "password_hash": pwd_hash,
            "name": u["name"],
            "is_admin": u["is_admin"],
            "favorite_category_ids": [],
            "stats": UserStats().model_dump(),
            "entitlements": UserEntitlements().model_dump(),
            "created_at": now,
            "updated_at": now,
        }
        col.insert_one(doc)
        docs.append(doc)
    print(f"Inserted {len(docs)} users (password: {DUMMY_PASSWORD}).")
    return docs


def seed_products(db):
    col = db["products"]
    if col.count_documents({}) > 0:
        return list(col.find())
    now = datetime.now(timezone.utc)
    products = [
        {"_id": ObjectId(), "name_ar": "حزمة 5 جولات", "name_en": "5 Rounds Pack", "type": "rounds", "rounds": 5, "price_display": "مجاني", "active": True, "created_at": now},
        {"_id": ObjectId(), "name_ar": "حزمة 20 جولة", "name_en": "20 Rounds Pack", "type": "rounds", "rounds": 20, "price_display": "9.99 ر.س", "active": True, "created_at": now},
        {"_id": ObjectId(), "name_ar": "اشتراك شهري", "name_en": "Monthly Subscription", "type": "subscription", "rounds": None, "price_display": "29.99 ر.س", "active": True, "created_at": now},
    ]
    col.insert_many(products)
    print(f"Inserted {len(products)} products.")
    return products


def seed_matches(db, user_ids, category_ids):
    col = db["matches"]
    if col.count_documents({}) > 3:
        print("Matches already exist, skipping.")
        return []
    if not user_ids or not category_ids:
        print("Need users and categories for matches, skipping.")
        return []
    now = datetime.now(timezone.utc)
    matches = []
    for i, uid in enumerate(user_ids[:3]):
        cat_ids = list(category_ids[: (2 + i)])
        status = "finished" if i == 0 else ("active" if i == 1 else "finished")
        doc = {
            "_id": ObjectId(),
            "created_by_user_id": uid,
            "mode": "team",
            "status": status,
            "selected_category_ids": cat_ids,
            "teams": {"A": {"name": "فريق أ", "avatar_key": None, "score": 100 if i == 0 else 0}, "B": {"name": "فريق ب", "avatar_key": None, "score": 50 if i == 0 else 0}},
            "settings": {
                "timer_seconds": 10,
                "max_categories": 6,
                "levels": [
                    {"level": 1, "points": 100, "questions_per_level": 2},
                    {"level": 2, "points": 200, "questions_per_level": 2},
                    {"level": 3, "points": 500, "questions_per_level": 2},
                ],
                "allow_negative_points": False,
            },
            "progress": {"usage": []},
            "rounds": [],
            "finished_at": now if i == 0 else None,
            "created_at": now,
            "updated_at": now,
        }
        col.insert_one(doc)
        matches.append(doc)
    print(f"Inserted {len(matches)} matches.")
    return matches


def seed_purchases(db, user_ids, product_ids):
    col = db["purchases"]
    if col.count_documents({}) > 0:
        return []
    if not user_ids or not product_ids:
        return []
    now = datetime.now(timezone.utc)
    rounds_products = [p["_id"] for p in product_ids if p.get("type") == "rounds"]
    purchases = []
    for i, uid in enumerate(user_ids[:3]):
        pid = rounds_products[i % len(rounds_products)] if rounds_products else product_ids[0]["_id"]
        doc = {
            "_id": ObjectId(),
            "user_id": uid,
            "product_id": pid,
            "provider": "seed",
            "provider_ref": f"seed-{i}",
            "rounds_delta": 5,
            "subscription_expires_at": None,
            "created_at": now,
        }
        col.insert_one(doc)
        purchases.append(doc)
    print(f"Inserted {len(purchases)} purchases.")
    return purchases


def main():
    init_db()
    db = get_db()
    categories = seed_categories(db)
    category_ids = [c["_id"] for c in categories]
    seed_questions(db, category_ids)
    users = seed_users(db)
    user_ids = [u["_id"] for u in users]
    products = seed_products(db)
    seed_matches(db, user_ids, category_ids)
    seed_purchases(db, user_ids, products)
    print("Seed done. Users password:", DUMMY_PASSWORD)
    print("Dummy logins: ahmed@example.com, sara@example.com, demo@example.com")
    print("Admin logins: demo@example.com, admin@example.com")
    print("Collections: categories, questions, users, products, matches, purchases")


if __name__ == "__main__":
    main()
