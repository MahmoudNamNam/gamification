"""
Migration: Convert old questions (with answers/correct) to new format.
- Keeps: prompt, hint, category_id, status, created_at, updated_at
- Drops: answers, correct
- Adds: level (1|2|3), points (100|200|500) from old difficulty/points if present

Run from backend dir: python -m scripts.migrate_questions_to_no_answers
Ensure MONGODB_URI and MONGODB_DB_NAME are set.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import get_db, init_db, get_questions_collection

# Old difficulty -> (level, points)
DIFFICULTY_MAP = {
    "easy": (1, 100),
    "medium": (2, 200),
    "hard": (3, 500),
}


def normalize_prompt(old_prompt: dict) -> dict:
    """Ensure prompt has { text, media } shape. Old ContentBlock may have text_ar, text_en, text."""
    if not old_prompt:
        return {"text": None, "media": None}
    text = old_prompt.get("text") or old_prompt.get("text_ar") or old_prompt.get("text_en")
    media = old_prompt.get("media")
    return {"text": text, "media": media}


def normalize_hint_content(content: dict | None) -> dict | None:
    if not content:
        return None
    text = content.get("text") or content.get("text_ar") or content.get("text_en")
    media = content.get("media")
    return {"text": text, "media": media}


def migrate_one(doc: dict) -> dict:
    """Produce new question document (no answers/correct, has level/points, normalized prompt/hint)."""
    level, points = 1, 100
    if "difficulty" in doc:
        level, points = DIFFICULTY_MAP.get(doc["difficulty"], (1, 100))
    if "points" in doc and doc["points"] in (100, 200, 500):
        points = doc["points"]
        level = {100: 1, 200: 2, 500: 3}[points]
    new_doc = {
        "category_id": doc["category_id"],
        "level": level,
        "points": points,
        "prompt": normalize_prompt(doc.get("prompt") or {}),
        "hint": {
            "enabled": bool((doc.get("hint") or {}).get("enabled")),
            "content": normalize_hint_content((doc.get("hint") or {}).get("content")),
        },
        "status": doc.get("status", "active"),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": datetime.now(timezone.utc),
    }
    return new_doc


def main():
    init_db()
    col = get_questions_collection()
    cursor = col.find({})
    updated = 0
    for doc in cursor:
        if "answers" in doc or "correct" in doc or "level" not in doc:
            new_doc = migrate_one(doc)
            new_doc["_id"] = doc["_id"]
            col.replace_one({"_id": doc["_id"]}, new_doc)
            updated += 1
    print(f"Migrated {updated} questions.")


if __name__ == "__main__":
    main()
