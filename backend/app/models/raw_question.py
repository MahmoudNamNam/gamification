"""
Raw question data for import. Store q, hint, answer(s), level as simple strings;
convert to Question (ContentBlock) when importing.
"""

from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from app.utils.objectid import PyObjectId


class RawAnswerOption(BaseModel):
    """Single answer in raw form: key and text (and optional image URL later)."""

    key: Literal["A", "B", "C", "D"]
    text: str = Field(..., description="Answer text (plain)")


class RawQuestion(BaseModel):
    """
    Stored raw data: q, hint, answers, level.
    Extract these to build a full Question (prompt, hint, answers, difficulty, points).
    """

    id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = Field(None, description="Set when importing into a category")
    # Extract these into Question:
    q: str = Field(..., description="Question text (and/or image URL in future)")
    hint: Optional[str] = Field(None, description="Hint text")
    answers: list[RawAnswerOption] = Field(default_factory=list, description="Answer options A–D with text")
    correct: Union[str, list[str]] = Field(
        default="A",
        description="Correct key(s): 'A' or ['A'] for single, ['A','B'] for multi",
    )
    level: Union[str, int] = Field(
        default="medium",
        description="Difficulty: 'easy'|'medium'|'hard' or 1|2|3 (1=easy, 2=medium, 3=hard)",
    )
    # Import status
    status: Literal["pending", "imported", "failed"] = "pending"
    tags: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Optional: link to source file or batch
    source: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class RawQuestionCreate(BaseModel):
    """Payload to create a raw question (e.g. from CSV/JSON import)."""

    category_id: Optional[str] = None
    q: str
    hint: Optional[str] = None
    answers: list[RawAnswerOption] = []
    correct: Union[str, list[str]] = "A"
    level: Union[str, int] = "medium"
    tags: list[str] = []
    source: Optional[str] = None
