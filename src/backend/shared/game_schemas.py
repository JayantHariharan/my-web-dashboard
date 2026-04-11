# src/backend/shared/game_schemas.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GameBase(BaseModel):
    game_type: str = Field(..., examples=["single", "multi"])
    level: str = Field("medium", examples=["easy", "medium", "hard", "god"])
    capacity: int = Field(2, ge=2, le=4)

class GameCreate(GameBase):
    pass

class GamePlayer(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    is_ai: bool = False
    symbol: str
    team_index: int

class GameResponse(BaseModel):
    id: int
    game_type: str
    status: str
    join_code: Optional[str] = None
    capacity: int
    level: str
    players: List[GamePlayer]
    created_at: datetime
    updated_at: datetime

class MoveCreate(BaseModel):
    game_id: int
    position: int = Field(..., ge=0, le=8)

class MoveResponse(BaseModel):
    id: int
    game_id: int
    player_id: Optional[int] = None
    symbol: str
    position: int
    created_at: datetime

class BoardState(BaseModel):
    board: List[Optional[str]] # ['X', 'O', None, ...]
    status: str # 'playing', 'X_wins', 'O_wins', 'draw'
    current_turn: str # 'X' or 'O'

class LeaderboardEntry(BaseModel):
    username: str
    wins: int
    losses: int
    draws: int
    elo_rating: int
