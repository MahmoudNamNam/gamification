from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_admin_user
from app.models.question import QuestionCreate, QuestionUpdate
from app.services.question_service import (
    create_question,
    list_questions,
    get_question_by_id,
    get_question_hint,
    get_question_answer,
    update_question,
    delete_question,
)
from app.core.errors import AppError, QUESTION_NOT_FOUND

router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])


@router.post("")
def admin_create_question(
    data: QuestionCreate,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    return create_question(data)


@router.get("")
def admin_list_questions(
    current_user: Annotated[dict, Depends(get_current_admin_user)],
    category_id: Optional[str] = Query(None),
    level: Optional[int] = Query(None, ge=1, le=3),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return list_questions(category_id=category_id, level=level, status=status, skip=skip, limit=limit)


@router.get("/{question_id}")
def admin_get_question(
    question_id: str,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    q = get_question_by_id(question_id)
    if not q:
        raise AppError(QUESTION_NOT_FOUND, "Question not found", status_code=404)
    return q


@router.get("/{question_id}/hint")
def admin_get_question_hint(
    question_id: str,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    """Get hint for a question (enabled flag + content)."""
    hint = get_question_hint(question_id)
    if hint is None:
        raise AppError(QUESTION_NOT_FOUND, "Question not found", status_code=404)
    return hint


@router.get("/{question_id}/answer")
def admin_get_question_answer(
    question_id: str,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    """Get answer for a question."""
    result = get_question_answer(question_id)
    if result is None:
        raise AppError(QUESTION_NOT_FOUND, "Question not found", status_code=404)
    return result


@router.patch("/{question_id}")
def admin_update_question(
    question_id: str,
    data: QuestionUpdate,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    q = update_question(question_id, data)
    if not q:
        raise AppError(QUESTION_NOT_FOUND, "Question not found", status_code=404)
    return q


@router.delete("/{question_id}")
def admin_delete_question(
    question_id: str,
    current_user: Annotated[dict, Depends(get_current_admin_user)],
):
    ok = delete_question(question_id)
    if not ok:
        raise AppError(QUESTION_NOT_FOUND, "Question not found", status_code=404)
    return {"deleted": True}
