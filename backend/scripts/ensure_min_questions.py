"""
Ensure every category has at least 2 active questions per level (1, 2, 3).
Inserts dummy questions only where count is below 2. Safe to run multiple times.

Run from backend dir: python -m scripts.ensure_min_questions
"""
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import init_db, get_categories_collection, get_questions_collection

MIN_PER_LEVEL = 2
LEVELS = [(1, 100), (2, 200), (3, 500)]
DUMMY_PROMPTS = [
    "سؤال إضافي في هذا المستوى.",
    "سؤال تجريبي للمستوى.",
]


def prompt_block(text: str) -> dict:
    return {
        "text": text,
        "media": None,
    }


def main():
    init_db()
    categories = list(get_categories_collection().find({"active": True}).sort("order", 1))
    questions_col = get_questions_collection()
    inserted = 0
    now = datetime.now(timezone.utc)
    for cat in categories:
        cid = cat["_id"]
        for level, points in LEVELS:
            count = questions_col.count_documents({
                "category_id": cid,
                "level": level,
                "status": "active",
            })
            need = max(0, MIN_PER_LEVEL - count)
            for i in range(need):
                prompt = DUMMY_PROMPTS[i % len(DUMMY_PROMPTS)]
                questions_col.insert_one({
                    "category_id": cid,
                    "level": level,
                    "points": points,
                    "prompt": prompt_block(prompt),
                    "hint": {"enabled": False, "content": None},
                    "answer": prompt_block("إجابة تجريبية."),
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                })
                inserted += 1
    print(f"Inserted {inserted} questions so every category has at least {MIN_PER_LEVEL} per level.")


if __name__ == "__main__":
    main()
