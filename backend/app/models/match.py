from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.utils.objectid import PyObjectId


# --- Teams & settings ---

class TeamInfo(BaseModel):
    name: str = ""
    avatar_key: Optional[str] = None
    score: int = 0


class LevelSetting(BaseModel):
    level: Literal[1, 2, 3]
    points: int  # 100, 200, 500
    questions_per_level: int = 2


class MatchSettings(BaseModel):
    timer_seconds: int = 10
    max_categories: int = 6
    levels: list[LevelSetting] = Field(
        default_factory=lambda: [
            LevelSetting(level=1, points=100, questions_per_level=2),
            LevelSetting(level=2, points=200, questions_per_level=2),
            LevelSetting(level=3, points=500, questions_per_level=2),
        ]
    )
    allow_negative_points: bool = False


# --- Progress: usage per category+level ---

class CategoryLevelUsage(BaseModel):
    category_id: PyObjectId
    level: Literal[1, 2, 3]
    used_question_ids: list[PyObjectId] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# --- Rounds (judge flow) ---

JudgeSelection = Literal["TEAM_A", "TEAM_B", "NO_ONE"]
ScoredTeam = Literal["A", "B"]


class MatchRound(BaseModel):
    round_no: int
    category_id: Optional[PyObjectId] = None
    level: Optional[Literal[1, 2, 3]] = None
    points: int = 0
    question_id: Optional[PyObjectId] = None
    judge_selection: Optional[JudgeSelection] = None
    scored_team: Optional[ScoredTeam] = None
    scored_points: int = 0
    created_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True


# --- Match ---

class Match(BaseModel):
    id: Optional[PyObjectId] = None
    created_by_user_id: PyObjectId
    mode: Literal["team", "solo"] = "team"
    status: Literal["active", "finished", "abandoned"] = "active"
    selected_category_ids: list[PyObjectId] = Field(..., max_length=6)
    teams: dict[str, TeamInfo] = Field(default_factory=lambda: {"A": TeamInfo(), "B": TeamInfo()})
    settings: MatchSettings = MatchSettings()
    progress: dict = Field(default_factory=lambda: {"usage": []})  # usage: list of CategoryLevelUsage-like dicts
    rounds: list[MatchRound] = []
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# --- Request/Response DTOs ---

class CreateMatchRequest(BaseModel):
    selected_category_ids: list[str] = Field(..., min_length=1, max_length=20)  # validated in service: max 6
    teamA_name: str = ""
    teamB_name: str = ""
    timer_seconds: Optional[int] = Field(None, ge=1, le=300)


class PatchTeamsRequest(BaseModel):
    teamA_name: Optional[str] = None
    teamB_name: Optional[str] = None
    avatar_keyA: Optional[str] = None
    avatar_keyB: Optional[str] = None


class NextQuestionRequest(BaseModel):
    category_id: str
    level: Literal[1, 2, 3]


class JudgeRequest(BaseModel):
    round_no: int
    judge_selection: Literal["TEAM_A", "TEAM_B", "NO_ONE"]


class NextQuestionResponse(BaseModel):
    match_id: str
    round_no: int
    timer_seconds: int
    category_id: str
    level: Literal[1, 2, 3]
    points: int
    question: dict  # GameQuestionResponse shape


class JudgeResponse(BaseModel):
    ok: bool = True
    scores: dict  # { teamA: int, teamB: int }
    last_round: dict  # { round_no, judge_selection, scored_points }


class FinishResponse(BaseModel):
    status: Literal["finished"]
    scores: dict  # { teamA: int, teamB: int }
    winner: dict  # { result: "TEAM_A"|"TEAM_B"|"DRAW", name: str|null }
    summary: dict  # { teamA_correct, teamB_correct, no_one, total_rounds }
