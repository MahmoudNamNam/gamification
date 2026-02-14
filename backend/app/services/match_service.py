from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from pymongo.collection import Collection

from app.core.db import get_matches_collection, get_categories_collection
from app.core.errors import (
    AppError,
    MAX_CATEGORIES_EXCEEDED,
    NO_QUESTIONS_LEFT_FOR_LEVEL,
    LEVEL_QUOTA_EXCEEDED,
    ROUND_ALREADY_JUDGED,
    ROUND_NOT_FOUND,
    MATCH_NOT_FOUND,
    MATCH_NOT_ACTIVE,
    MATCH_ALREADY_FINISHED,
)
from app.services.question_service import (
    get_question_by_id,
    get_question_hint,
    get_question_answer,
    get_answers_by_question_ids,
    pick_next_question,
)
from app.services.wallet_service import can_start_match, use_free_round, consume_round
from app.utils.objectid import to_objectid

LEVEL_POINTS = {1: 100, 2: 200, 3: 500}
DEFAULT_QUESTIONS_PER_LEVEL = 2


def _get_questions_per_level(match_doc: dict, level: int) -> int:
    """Max questions allowed per (category, level) from match settings; default 2."""
    for entry in match_doc.get("settings", {}).get("levels", []):
        if entry.get("level") == level:
            return max(1, int(entry.get("questions_per_level", DEFAULT_QUESTIONS_PER_LEVEL)))
    return DEFAULT_QUESTIONS_PER_LEVEL


def get_matches() -> Collection:
    return get_matches_collection()


def get_categories() -> Collection:
    return get_categories_collection()


def _match_doc_to_response(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(doc["_id"])
    for k in ("created_by_user_id", "selected_category_ids", "finished_at"):
        if k in out and out[k] is not None:
            if k == "selected_category_ids" and isinstance(out[k], list):
                out[k] = [str(x) for x in out[k]]
            elif k != "finished_at" and isinstance(out[k], list):
                out[k] = [str(x) for x in out[k]]
            elif hasattr(out[k], "__str__") and not isinstance(out[k], datetime):
                out[k] = str(out[k])
    if "rounds" in out:
        for r in out["rounds"]:
            for f in ("category_id", "question_id"):
                if r.get(f):
                    r[f] = str(r[f])
        qids = [r["question_id"] for r in out["rounds"] if r.get("question_id")]
        answers_map = get_answers_by_question_ids(qids)
        for r in out["rounds"]:
            qid = r.get("question_id")
            r["answer"] = answers_map.get(qid, {}).get("answer") if qid else None
    if "progress" in out and "usage" in out["progress"]:
        for u in out["progress"]["usage"]:
            if u.get("category_id"):
                u["category_id"] = str(u["category_id"])
            if u.get("used_question_ids"):
                u["used_question_ids"] = [str(x) for x in u["used_question_ids"]]
    out.pop("_id", None)
    return out


def _default_settings(timer_seconds: Optional[int] = None) -> dict:
    return {
        "timer_seconds": timer_seconds or 10,
        "max_categories": 6,
        "levels": [
            {"level": 1, "points": 100, "questions_per_level": 2},
            {"level": 2, "points": 200, "questions_per_level": 2},
            {"level": 3, "points": 500, "questions_per_level": 2},
        ],
        "allow_negative_points": False,
    }


def create_match(
    user_id: str,
    selected_category_ids: list[str],
    teamA_name: str = "",
    teamB_name: str = "",
    timer_seconds: Optional[int] = None,
) -> dict:
    if len(selected_category_ids) > 6:
        raise AppError(
            MAX_CATEGORIES_EXCEEDED,
            "Maximum 6 categories allowed",
            status_code=400,
            details={"max": 6},
        )
    cats = get_categories()
    oids = []
    for cid in selected_category_ids:
        if not ObjectId.is_valid(cid):
            raise AppError("INVALID_CATEGORIES", "Invalid category id", status_code=400, details={"category_id": cid})
        cat = cats.find_one({"_id": ObjectId(cid), "active": True})
        if not cat:
            raise AppError("INVALID_CATEGORIES", "Category not found or inactive", status_code=400, details={"category_id": cid})
        oids.append(ObjectId(cid))
    can_start, use_free = can_start_match(user_id)
    if not can_start:
        raise AppError("NO_ROUNDS_AVAILABLE", "No rounds available. Use free round or purchase rounds.", status_code=403)
    if use_free:
        use_free_round(user_id)
    else:
        consume_round(user_id)
    now = datetime.now(timezone.utc)
    settings = _default_settings(timer_seconds)
    doc = {
        "created_by_user_id": ObjectId(user_id),
        "mode": "team",
        "status": "active",
        "selected_category_ids": oids,
        "teams": {
            "A": {"name": teamA_name, "avatar_key": None, "score": 0},
            "B": {"name": teamB_name, "avatar_key": None, "score": 0},
        },
        "settings": settings,
        "progress": {"usage": []},
        "rounds": [],
        "finished_at": None,
        "created_at": now,
        "updated_at": now,
    }
    r = get_matches().insert_one(doc)
    doc["_id"] = r.inserted_id
    return _match_doc_to_response(doc)


def get_match(match_id: str, user_id: str) -> Optional[dict]:
    if not ObjectId.is_valid(match_id):
        return None
    doc = get_matches().find_one({"_id": ObjectId(match_id), "created_by_user_id": ObjectId(user_id)})
    return _match_doc_to_response(doc) if doc else None


def list_matches(
    user_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    q = {"created_by_user_id": ObjectId(user_id)}
    if status:
        q["status"] = status
    cursor = get_matches().find(q).sort("created_at", -1).skip(skip).limit(limit)
    return [_match_doc_to_response(d) for d in cursor]


def delete_match(match_id: str, user_id: str) -> bool:
    if not ObjectId.is_valid(match_id):
        return False
    result = get_matches().delete_one(
        {"_id": ObjectId(match_id), "created_by_user_id": ObjectId(user_id)}
    )
    return result.deleted_count > 0


def get_match_internal(match_id: str) -> Optional[dict]:
    if not ObjectId.is_valid(match_id):
        return None
    return get_matches().find_one({"_id": ObjectId(match_id)})


def _get_used_question_ids_for_level(match_doc: dict, category_id: ObjectId, level: int) -> list[ObjectId]:
    usage_list = match_doc.get("progress", {}).get("usage", [])
    cid_str = str(category_id)
    for u in usage_list:
        cid = u.get("category_id")
        if str(cid) == cid_str and u.get("level") == level:
            raw = u.get("used_question_ids") or []
            return [ObjectId(x) if not isinstance(x, ObjectId) else x for x in raw]
    return []


def _ensure_usage_entry(match_id: str, category_id: ObjectId, level: int, question_id: ObjectId) -> None:
    """Append question_id to progress.usage for this category+level; create entry if missing."""
    col = get_matches()
    doc = col.find_one({"_id": ObjectId(match_id)})
    if not doc:
        return
    usage_list = list(doc.get("progress", {}).get("usage", []))
    cid_str = str(category_id)
    found = False
    for u in usage_list:
        if str(u.get("category_id")) == cid_str and u.get("level") == level:
            used = list(u.get("used_question_ids") or [])
            qid_str = str(question_id)
            if not any(str(x) == qid_str for x in used):
                used.append(question_id)
            u["used_question_ids"] = used
            found = True
            break
    if not found:
        usage_list.append({
            "category_id": category_id,
            "level": level,
            "used_question_ids": [question_id],
        })
    col.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"progress.usage": usage_list, "updated_at": datetime.now(timezone.utc)}},
    )


def get_round_hint(match_id: str, user_id: str, round_no: int) -> dict:
    """Get hint for a round's question. Caller must be match owner."""
    match_doc = get_match_internal(match_id)
    if not match_doc or str(match_doc["created_by_user_id"]) != user_id:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    rounds_list = match_doc.get("rounds", [])
    round_entry = next((r for r in rounds_list if r.get("round_no") == round_no), None)
    if not round_entry:
        raise AppError(ROUND_NOT_FOUND, "Round not found", status_code=404, details={"round_no": round_no})
    question_id = round_entry.get("question_id")
    if not question_id:
        raise AppError(ROUND_NOT_FOUND, "Round has no question", status_code=404, details={"round_no": round_no})
    qid_str = str(question_id)
    hint = get_question_hint(qid_str)
    if hint is None:
        raise AppError("QUESTION_NOT_FOUND", "Question not found", status_code=404)
    return hint


def get_round_answer(match_id: str, user_id: str, round_no: int) -> dict:
    """Get answer for a round's question. Caller must be match owner."""
    match_doc = get_match_internal(match_id)
    if not match_doc or str(match_doc["created_by_user_id"]) != user_id:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    rounds_list = match_doc.get("rounds", [])
    round_entry = next((r for r in rounds_list if r.get("round_no") == round_no), None)
    if not round_entry:
        raise AppError(ROUND_NOT_FOUND, "Round not found", status_code=404, details={"round_no": round_no})
    question_id = round_entry.get("question_id")
    if not question_id:
        raise AppError(ROUND_NOT_FOUND, "Round has no question", status_code=404, details={"round_no": round_no})
    qid_str = str(question_id)
    result = get_question_answer(qid_str)
    if result is None:
        raise AppError("QUESTION_NOT_FOUND", "Question not found", status_code=404)
    return result


def next_question(
    match_id: str,
    user_id: str,
    category_id: str,
    level: Literal[1, 2, 3],
) -> dict:
    match_doc = get_match_internal(match_id)
    if not match_doc or str(match_doc["created_by_user_id"]) != user_id:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    if match_doc.get("status") != "active":
        raise AppError(MATCH_NOT_ACTIVE, "Match is not active", status_code=400)
    selected = match_doc.get("selected_category_ids", [])
    cid_oid = ObjectId(category_id) if ObjectId.is_valid(category_id) else None
    if not cid_oid or cid_oid not in selected:
        msg = "Category not in selected categories. Use a category_id from this match's selected_category_ids (not the match id)."
        if match_id == category_id:
            msg = "Use a category_id from selected_category_ids, not the match id."
        raise AppError("INVALID_CATEGORIES", msg, status_code=400, details={"category_id": category_id, "selected_category_ids": [str(x) for x in selected]})
    max_per_level = _get_questions_per_level(match_doc, level)
    used = _get_used_question_ids_for_level(match_doc, cid_oid, level)
    if len(used) >= max_per_level:
        raise AppError(
            LEVEL_QUOTA_EXCEEDED,
            f"Level quota exceeded (max {max_per_level} questions per category per level)",
            status_code=409,
            details={"category_id": category_id, "level": level, "max_per_level": max_per_level},
        )
    question = pick_next_question(cid_oid, level, used)
    if not question:
        raise AppError(
            NO_QUESTIONS_LEFT_FOR_LEVEL,
            "No questions left for this category and level",
            status_code=409,
            details={"category_id": category_id, "level": level},
        )
    points = LEVEL_POINTS[level]
    round_no = len(match_doc.get("rounds", [])) + 1
    qid_oid = ObjectId(question["id"])
    now = datetime.now(timezone.utc)
    round_entry = {
        "round_no": round_no,
        "category_id": cid_oid,
        "level": level,
        "points": points,
        "question_id": qid_oid,
        "judge_selection": None,
        "scored_team": None,
        "scored_points": 0,
        "created_at": now,
    }
    get_matches().update_one(
        {"_id": ObjectId(match_id)},
        {
            "$set": {"updated_at": now},
            "$push": {"rounds": round_entry},
        },
    )
    _ensure_usage_entry(match_id, cid_oid, level, qid_oid)
    timer_seconds = match_doc.get("settings", {}).get("timer_seconds", 10)
    hint_available = bool(question.get("hint", {}).get("enabled"))
    prompt = question.get("prompt") or {}
    return {
        "match_id": match_id,
        "round_no": round_no,
        "timer_seconds": timer_seconds,
        "category_id": category_id,
        "level": level,
        "points": points,
        "question": {
            "id": question["id"],
            "prompt": prompt,
            "hint_available": hint_available,
        },
    }


def judge_round(
    match_id: str,
    user_id: str,
    round_no: int,
    judge_selection: Literal["TEAM_A", "TEAM_B", "NO_ONE"],
) -> dict:
    match_doc = get_match_internal(match_id)
    if not match_doc or str(match_doc["created_by_user_id"]) != user_id:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    if match_doc.get("status") != "active":
        raise AppError(MATCH_NOT_ACTIVE, "Match is not active", status_code=400)
    rounds_list = match_doc.get("rounds", [])
    round_entry = next((r for r in rounds_list if r.get("round_no") == round_no), None)
    if not round_entry:
        raise AppError(ROUND_NOT_FOUND, "Round not found", status_code=404, details={"round_no": round_no})
    if round_entry.get("judge_selection") is not None:
        raise AppError(
            ROUND_ALREADY_JUDGED,
            "Round already judged",
            status_code=409,
            details={"round_no": round_no},
        )
    points = round_entry.get("points", 0)
    scored_team = None
    scored_points = 0
    if judge_selection == "TEAM_A":
        scored_team = "A"
        scored_points = points
    elif judge_selection == "TEAM_B":
        scored_team = "B"
        scored_points = points
    teams = match_doc.get("teams", {"A": {"score": 0}, "B": {"score": 0}})
    new_a = teams.get("A", {}).get("score", 0) + (scored_points if scored_team == "A" else 0)
    new_b = teams.get("B", {}).get("score", 0) + (scored_points if scored_team == "B" else 0)
    get_matches().update_one(
        {"_id": ObjectId(match_id), "rounds.round_no": round_no},
        {
            "$set": {
                "rounds.$.judge_selection": judge_selection,
                "rounds.$.scored_team": scored_team,
                "rounds.$.scored_points": scored_points,
                "teams.A.score": new_a,
                "teams.B.score": new_b,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return {
        "ok": True,
        "scores": {"teamA": new_a, "teamB": new_b},
        "last_round": {
            "round_no": round_no,
            "judge_selection": judge_selection,
            "scored_points": scored_points,
        },
    }


def finish_match(match_id: str, user_id: str) -> dict:
    match_doc = get_match_internal(match_id)
    if not match_doc or str(match_doc["created_by_user_id"]) != user_id:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    if match_doc.get("status") == "finished":
        raise AppError(MATCH_ALREADY_FINISHED, "Match already finished", status_code=400)
    now = datetime.now(timezone.utc)
    teams = match_doc.get("teams", {"A": {"name": "", "score": 0}, "B": {"name": "", "score": 0}})
    teamA_score = teams.get("A", {}).get("score", 0)
    teamB_score = teams.get("B", {}).get("score", 0)
    teamA_name = teams.get("A", {}).get("name", "Team A")
    teamB_name = teams.get("B", {}).get("name", "Team B")
    rounds_list = match_doc.get("rounds", [])
    teamA_correct = sum(1 for r in rounds_list if r.get("judge_selection") == "TEAM_A")
    teamB_correct = sum(1 for r in rounds_list if r.get("judge_selection") == "TEAM_B")
    no_one = sum(1 for r in rounds_list if r.get("judge_selection") == "NO_ONE")
    if teamA_score > teamB_score:
        winner_result = "TEAM_A"
        winner_name = teamA_name
    elif teamB_score > teamA_score:
        winner_result = "TEAM_B"
        winner_name = teamB_name
    else:
        winner_result = "DRAW"
        winner_name = None
    get_matches().update_one(
        {"_id": ObjectId(match_id)},
        {
            "$set": {
                "status": "finished",
                "finished_at": now,
                "updated_at": now,
            }
        },
    )
    return {
        "status": "finished",
        "scores": {"teamA": teamA_score, "teamB": teamB_score},
        "winner": {"result": winner_result, "name": winner_name},
        "summary": {
            "teamA_correct": teamA_correct,
            "teamB_correct": teamB_correct,
            "no_one": no_one,
            "total_rounds": len(rounds_list),
        },
    }


# --- Optional: keep patch_teams for client to set names after create if not in body
def patch_teams(
    match_id: str,
    user_id: str,
    teamA_name: Optional[str],
    teamB_name: Optional[str],
    avatar_keyA: Optional[str],
    avatar_keyB: Optional[str],
) -> dict:
    match_doc = get_match_internal(match_id)
    if not match_doc or str(match_doc["created_by_user_id"]) != user_id:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    if match_doc.get("status") != "active":
        raise AppError(MATCH_NOT_ACTIVE, "Match is not active", status_code=400)
    update = {}
    if teamA_name is not None:
        update["teams.A.name"] = teamA_name
    if teamB_name is not None:
        update["teams.B.name"] = teamB_name
    if avatar_keyA is not None:
        update["teams.A.avatar_key"] = avatar_keyA
    if avatar_keyB is not None:
        update["teams.B.avatar_key"] = avatar_keyB
    if update:
        update["updated_at"] = datetime.now(timezone.utc)
        get_matches().update_one({"_id": ObjectId(match_id)}, {"$set": update})
    return get_match(match_id, user_id)
