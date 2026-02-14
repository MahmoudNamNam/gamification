from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from pymongo.collection import Collection

from app.core.db import get_questions_collection
from app.core.errors import AppError, QUESTION_NOT_FOUND
from app.models.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionHint,
    PromptBlock,
)
from app.utils.objectid import to_objectid


def get_questions_col() -> Collection:
    return get_questions_collection()


def create_question(data: QuestionCreate) -> dict:
    col = get_questions_col()
    now = datetime.now(timezone.utc)
    doc = {
        "category_id": to_objectid(data.category_id),
        "level": data.level,
        "points": data.points,
        "prompt": data.prompt.model_dump(),
        "hint": data.hint.model_dump() if data.hint else {"enabled": False, "content": None},
        "answer": data.answer.model_dump() if data.answer else None,
        "status": data.status,
        "created_at": now,
        "updated_at": now,
    }
    r = col.insert_one(doc)
    doc["_id"] = r.inserted_id
    return _doc_to_question(doc)


def list_questions(
    category_id: Optional[str] = None,
    level: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    col = get_questions_col()
    q = {}
    if category_id:
        q["category_id"] = to_objectid(category_id)
    if level is not None:
        q["level"] = level
    if status:
        q["status"] = status
    cursor = col.find(q).skip(skip).limit(limit).sort("created_at", -1)
    return [_doc_to_question(d) for d in cursor]


def get_question_by_id(question_id: str) -> Optional[dict]:
    col = get_questions_col()
    if not ObjectId.is_valid(question_id):
        return None
    doc = col.find_one({"_id": ObjectId(question_id)})
    return _doc_to_question(doc) if doc else None


def get_question_hint(question_id: str) -> Optional[dict]:
    """Return hint for a question: { \"enabled\": bool, \"content\": PromptBlock or None }. None if question not found."""
    col = get_questions_col()
    if not ObjectId.is_valid(question_id):
        return None
    doc = col.find_one({"_id": ObjectId(question_id)}, {"_id": 0, "hint": 1})
    if not doc or "hint" not in doc:
        return None
    return doc["hint"]


def get_question_answer(question_id: str) -> Optional[dict]:
    """Return answer for a question: { \"answer\": PromptBlock or None }. None if question not found."""
    col = get_questions_col()
    if not ObjectId.is_valid(question_id):
        return None
    doc = col.find_one({"_id": ObjectId(question_id)}, {"_id": 0, "answer": 1})
    if doc is None:
        return None
    return {"answer": doc.get("answer")}


def get_answers_by_question_ids(question_ids: list) -> dict[str, dict]:
    """Return map question_id (str) -> { \"answer\": PromptBlock or None } for match rounds."""
    if not question_ids:
        return {}
    col = get_questions_col()
    oids = [ObjectId(qid) for qid in question_ids if ObjectId.is_valid(qid)]
    if not oids:
        return {}
    cursor = col.find({"_id": {"$in": oids}}, {"_id": 1, "answer": 1})
    return {str(d["_id"]): {"answer": d.get("answer")} for d in cursor}


def update_question(question_id: str, data: QuestionUpdate) -> Optional[dict]:
    col = get_questions_col()
    if not ObjectId.is_valid(question_id):
        return None
    update = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "category_id" in update:
        update["category_id"] = to_objectid(update["category_id"])
    if "prompt" in update and hasattr(update["prompt"], "model_dump"):
        update["prompt"] = update["prompt"].model_dump()
    if "hint" in update and hasattr(update["hint"], "model_dump"):
        update["hint"] = update["hint"].model_dump()
    if "answer" in update and hasattr(update.get("answer"), "model_dump"):
        update["answer"] = update["answer"].model_dump()
    elif "answer" in update:
        update["answer"] = None
    if update:
        update["updated_at"] = datetime.now(timezone.utc)
        col.update_one({"_id": ObjectId(question_id)}, {"$set": update})
    return get_question_by_id(question_id)


def delete_question(question_id: str) -> bool:
    col = get_questions_col()
    if not ObjectId.is_valid(question_id):
        return False
    r = col.delete_one({"_id": ObjectId(question_id)})
    return r.deleted_count > 0


def _doc_to_question(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(doc["_id"])
    if "category_id" in out and hasattr(out["category_id"], "__str__"):
        out["category_id"] = str(out["category_id"])
    out.pop("_id", None)
    return out


# Level -> points mapping (L1=100, L2=200, L3=500)
LEVEL_POINTS: dict[int, int] = {1: 100, 2: 200, 3: 500}


def pick_next_question(
    category_id: ObjectId,
    level: Literal[1, 2, 3],
    used_question_ids: list[ObjectId],
) -> Optional[dict]:
    """
    Pick next unused active question for the given category and level.
    Excludes questions in used_question_ids.
    """
    col = get_questions_col()
    points = LEVEL_POINTS.get(level, 100)
    q = {
        "category_id": category_id,
        "level": level,
        "points": points,
        "status": "active",
        "_id": {"$nin": used_question_ids} if used_question_ids else {"$exists": True},
    }
    doc = col.find_one(q)
    return _doc_to_question(doc) if doc else None
