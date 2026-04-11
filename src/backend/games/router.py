# src/backend/games/router.py
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from ..shared.game_schemas import GameCreate, GameResponse, MoveCreate, MoveResponse, BoardState, LeaderboardEntry, GamePlayer
from ..shared.database import game_repo, game_player_repo, game_move_repo, leaderboard_repo, user_repo, activity_repo
from .service import GameService

router = APIRouter(prefix="/api/games", tags=["Games"])

@router.post("/tic-tac-toe/create", response_model=GameResponse)
async def create_game(data: GameCreate, user_id: int):
    """Creates a new game. If 'multi', generates a join code."""
    join_code = str(uuid.uuid4())[:6].upper() if data.game_type == "multi" else None
    
    game_id = game_repo.create({
        "game_type": data.game_type,
        "join_code": join_code,
        "capacity": data.capacity,
        "level": data.level,
        "status": "waiting" if data.game_type == "multi" else "playing"
    })
    
    # Log Activity
    activity_repo.log_activity(user_id, "game", "Tic-Tac-Toe Crystal", str(game_id))
    
    # Add creator as Player X
    game_player_repo.create({
        "game_id": game_id,
        "user_id": user_id,
        "is_ai": False,
        "symbol": "X",
        "team_index": 0
    })
    
    if data.game_type == "single":
        # Add AI as Player O
        game_player_repo.create({
            "game_id": game_id,
            "user_id": None,
            "is_ai": True,
            "symbol": "O",
            "team_index": 1
        })
    
    game = game_repo.get_by_id(game_id)
    players = game_player_repo.find_by_game(game_id)
    return {**game, "players": players}

@router.post("/tic-tac-toe/join", response_model=GameResponse)
async def join_game(join_code: str, user_id: int):
    """Joins an existing multiplayer game via code."""
    game = game_repo.find_by_code(join_code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Game already started or finished")
        
    players = game_player_repo.find_by_game(game["id"])
    if len(players) >= game["capacity"]:
        raise HTTPException(status_code=400, detail="Game is full")
        
    # Check if user already in game
    if any(p["user_id"] == user_id for p in players):
        return {**game, "players": players}
        
    # Join as next available symbol
    symbol = "O" if any(p["symbol"] == "X" for p in players) else "X"
    
    game_player_repo.create({
        "game_id": game["id"],
        "user_id": user_id,
        "is_ai": False,
        "symbol": symbol,
        "team_index": len(players)
    })
    
    # Log Activity
    activity_repo.log_activity(user_id, "game", "Tic-Tac-Toe Crystal", str(game["id"]))
    
    # Start game if full
    if len(players) + 1 == game["capacity"]:
        game_repo.update(game["id"], {"status": "playing"})
        
    updated_game = game_repo.get_by_id(game["id"])
    updated_players = game_player_repo.find_by_game(game["id"])
    return {**updated_game, "players": updated_players}

@router.post("/tic-tac-toe/move", response_model=MoveResponse)
async def make_move(data: MoveCreate, user_id: int):
    """Makes a move in an active game."""
    game = game_repo.get_by_id(data.game_id)
    if not game or game["status"] != "playing":
        raise HTTPException(status_code=400, detail="Game not active")
        
    board, status, turn = GameService.get_board_state(data.game_id)
    if status != 'playing':
        raise HTTPException(status_code=400, detail="Game already finished")
        
    players = game_player_repo.find_by_game(data.game_id)
    current_player = next((p for p in players if p["symbol"] == turn), None)
    
    if not current_player:
        raise HTTPException(status_code=500, detail="State error: No player for turn")
        
    if current_player["user_id"] != user_id:
        raise HTTPException(status_code=400, detail="Not your turn")
        
    if board[data.position] is not None:
        raise HTTPException(status_code=400, detail="Position occupied")
        
    # Record move
    move_id = game_move_repo.create({
        "game_id": data.game_id,
        "player_id": user_id,
        "symbol": turn,
        "position": data.position
    })
    
    # Trigger AI move if single player or team member missing (simplified here for single player)
    board, status, turn = GameService.get_board_state(data.game_id)
    if status == 'playing' and game["game_type"] == "single":
        ai_player = next((p for p in players if p["is_ai"] and p["symbol"] == turn), None)
        if ai_player:
            ai_pos = GameService.get_ai_move(board, turn, game["level"])
            game_move_repo.create({
                "game_id": data.game_id,
                "player_id": None,
                "symbol": turn,
                "position": ai_pos
            })
            board, status, turn = GameService.get_board_state(data.game_id)

    # If game finished, update status
    if status != 'playing':
        game_repo.update(data.game_id, {"status": "finished", "updated_at": "CURRENT_TIMESTAMP"})
        # Update leaderboard logic would go here
        
    move = game_move_repo.get_by_id(move_id)
    return move

@router.get("/tic-tac-toe/state/{game_id}", response_model=BoardState)
async def get_state(game_id: int):
    """Returns the current board, status, and turn."""
    board, status, turn = GameService.get_board_state(game_id)
    return {"board": board, "status": status, "current_turn": turn}

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(limit: int = 10):
    """Returns the top players."""
    return leaderboard_repo.get_top(limit)
