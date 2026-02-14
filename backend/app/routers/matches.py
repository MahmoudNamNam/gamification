from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.match import (
    CreateMatchRequest,
    PatchTeamsRequest,
    NextQuestionRequest,
    JudgeRequest,
)
from app.services import match_service
from app.core.errors import AppError, MATCH_NOT_FOUND

router = APIRouter(prefix="/matches", tags=["matches"])


def _current_user_id(current_user: dict) -> str:
    return str(current_user["_id"])


@router.get("")
def list_matches(
    current_user: Annotated[dict, Depends(get_current_user)],
    status: Optional[str] = Query(None, description="Filter by status: active, finished, abandoned"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List matches for the current user."""
    return match_service.list_matches(_current_user_id(current_user), status=status, skip=skip, limit=limit)


@router.post("")
def create_match(
    req: CreateMatchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new match. Select up to 6 categories and optional team names / timer."""
    return match_service.create_match(
        _current_user_id(current_user),
        req.selected_category_ids,
        teamA_name=req.teamA_name,
        teamB_name=req.teamB_name,
        timer_seconds=req.timer_seconds,
    )


@router.get("/{match_id}")
def get_match(
    match_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    m = match_service.get_match(match_id, _current_user_id(current_user))
    if not m:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    return m


@router.post("/{match_id}/next-question")
def next_question(
    match_id: str,
    req: NextQuestionRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Request the next question for a category+level. Max 2 questions per category per level."""
    return match_service.next_question(
        match_id,
        _current_user_id(current_user),
        req.category_id,
        req.level,
    )


@router.get("/{match_id}/rounds/{round_no}/hint")
def get_round_hint(
    match_id: str,
    round_no: int,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get hint for a round's question. Only the match owner can call this."""
    return match_service.get_round_hint(match_id, _current_user_id(current_user), round_no)


@router.get("/{match_id}/rounds/{round_no}/answer")
def get_round_answer(
    match_id: str,
    round_no: int,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get answer for a round's question. Only the match owner can call this."""
    return match_service.get_round_answer(match_id, _current_user_id(current_user), round_no)


@router.post("/{match_id}/judge")
def judge_round(
    match_id: str,
    req: JudgeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Submit judge selection for a round (TEAM_A, TEAM_B, or NO_ONE). Updates scores."""
    return match_service.judge_round(
        match_id,
        _current_user_id(current_user),
        req.round_no,
        req.judge_selection,
    )


@router.post("/{match_id}/finish")
def finish_match(
    match_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Mark match as finished. Returns final scores, winner (or draw), and summary stats."""
    return match_service.finish_match(match_id, _current_user_id(current_user))


@router.patch("/{match_id}/teams")
def patch_match_teams(
    match_id: str,
    req: PatchTeamsRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Optionally update team names/avatars before or during an active match."""
    return match_service.patch_teams(
        match_id,
        _current_user_id(current_user),
        req.teamA_name,
        req.teamB_name,
        req.avatar_keyA,
        req.avatar_keyB,
    )


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a match. Only the creator can delete."""
    ok = match_service.delete_match(match_id, _current_user_id(current_user))
    if not ok:
        raise AppError(MATCH_NOT_FOUND, "Match not found", status_code=404)
    return None
