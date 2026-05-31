from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


BingoLetter = Literal["B", "I", "N", "G", "O"]


class CardPreviewRequest(BaseModel):
    game_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)


class CardCell(BaseModel):
    row: int = Field(ge=0, le=4)
    col: int = Field(ge=0, le=4)
    letter: BingoLetter
    number: int | None = Field(default=None, ge=1, le=75)
    label: str
    marked: bool = False
    is_free: bool = False


class CardResponse(BaseModel):
    card_id: str = Field(default_factory=lambda: str(uuid4()))
    game_id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cells: list[list[CardCell]]
    marked_numbers: list[int] = Field(default_factory=list)


class MarkNumberRequest(BaseModel):
    number: int = Field(ge=1, le=75)


class MarkNumberResponse(BaseModel):
    matched: bool
    card: CardResponse


class RoomProgressRequest(BaseModel):
    user_ids: list[str] = Field(default_factory=list)
    winning_pattern: str = "top_row"


class PlayerProgressResponse(BaseModel):
    user_id: str
    progress: int = Field(ge=0)
    total: int = Field(ge=0)
    has_card: bool = False
    is_complete: bool = False


class WinnerCheckData(BaseModel):
    card_id: str
    game_id: str
    user_id: str
    rows: list[list[CardCell]]
    columns: list[list[CardCell]]
    diagonals: list[list[CardCell]]
    marked_numbers: list[int]
