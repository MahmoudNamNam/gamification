from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.content_block import MediaBlock
from app.utils.objectid import PyObjectId


class PromptBlock(BaseModel):
    """Text and/or media for question prompt or hint content."""

    text: Optional[str] = None
    media: Optional[MediaBlock] = None


class QuestionHint(BaseModel):
    enabled: bool = False
    content: Optional[PromptBlock] = Field(None, description="Hint text and/or media")


class Question(BaseModel):
    id: Optional[PyObjectId] = None
    category_id: PyObjectId
    level: Literal[1, 2, 3]
    points: Literal[100, 200, 500]
    prompt: PromptBlock = Field(..., description="Question text and/or media")
    hint: QuestionHint = QuestionHint()
    answer: Optional[PromptBlock] = Field(None, description="Answer text and/or media")
    status: Literal["active", "draft", "archived"] = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class QuestionCreate(BaseModel):
    category_id: str
    level: Literal[1, 2, 3]
    points: Literal[100, 200, 500]
    prompt: PromptBlock = Field(..., description="Question text and/or media")
    hint: QuestionHint = QuestionHint()
    answer: Optional[PromptBlock] = Field(None, description="Answer text and/or media")
    status: Literal["active", "draft", "archived"] = "active"


class QuestionUpdate(BaseModel):
    category_id: Optional[str] = None
    level: Optional[Literal[1, 2, 3]] = None
    points: Optional[Literal[100, 200, 500]] = None
    prompt: Optional[PromptBlock] = None
    hint: Optional[QuestionHint] = None
    answer: Optional[PromptBlock] = None
    status: Optional[Literal["active", "draft", "archived"]] = None


class GameQuestionResponse(BaseModel):
    """Question payload for next-question (prompt + hint_available; answer shown after round)."""

    id: str
    prompt: PromptBlock = Field(..., description="Question text and/or media")
    hint_available: bool
