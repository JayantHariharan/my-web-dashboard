"""
Games API router.
Handles game-specific endpoints like score submission and leaderboards.
"""

from fastapi import APIRouter, Request, HTTPException, status
from typing import List, Dict, Any, Optional
from ..shared.database import game_score_repo, user_repo
from ..shared.schemas import (
    GameScoreCreate,
    GameScoreResponse,
    LeaderboardResponse,
    LeaderboardEntry,
)
import logging

logger = logging.getLogger(__name__)
from ..shared.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("/", summary="List available games")
async def list_games():
    """
    Get list of available games.
    Currently returns static list; future: from app_registry.
    """
    # For now, return hardcoded games list
    # In future, query app_registry where category='game'
    games = [
        {
            "id": 1,
            "name": "tic-tac-toe",
            "title": "Tic-Tac-Toe Crystal",
            "description": "Classic Tic-Tac-Toe with AI opponent",
            "icon": "🎮",
            "route": "/apps/tic-tac-toe",
        }
    ]
    return {"success": True, "games": games}


@router.post("/{game_name}/scores", response_model=GameScoreResponse)
async def submit_score(game_name: str, score_data: GameScoreCreate, request: Request):
    """
    Submit a score for a game.

    ## Request Example
    ```json
    {
        "game_name": "tic-tac-toe",
        "score": 1500,
        "metadata": {
            "moves": 15,
            "opponent": "ai-easy",
            "won": true
        }
    }
    ```

    ## Response Example
    ```json
    {
        "id": 123,
        "user_id": 5,
        "game_name": "tic-tac-toe",
        "score": 1500,
        "metadata": {"moves": 15, "opponent": "ai-easy", "won": true},
        "created_at": "2025-03-29T16:30:00"
    }
    ```

    ## Rate Limiting
    - Games endpoints: 100 requests per hour per IP
    """
    # Get user from session or query param (demo - will be token-based)
    username = request.headers.get("X-Username") or request.query_params.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    user = user_repo.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Submit score
    score_id = game_score_repo.submit_score(
        user_id=user["id"],
        game_name=game_name,
        score=score_data.score,
        metadata=score_data.metadata,
    )

    logger.info(f"User {username} submitted score {score_data.score} for {game_name}")

    # Return the created score
    score = game_score_repo.get_by_id(score_id)
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score not found"
        )
    return GameScoreResponse(**score)


@router.get("/{game_name}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(game_name: str, limit: int = 10):
    """
    Get top scores leaderboard for a game.

    ## Query Parameters
    - `limit`: Number of entries to return (default 10, max 100)

    ## Response Example
    ```json
    {
        "success": true,
        "game_name": "tic-tac-toe",
        "entries": [
            {
                "rank": 1,
                "username": "champion123",
                "score": 2500,
                "created_at": "2025-03-29T14:20:00"
            }
        ],
        "total_entries": 150
    }
    ```
    """
    if not (1 <= limit <= 100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100",
        )

    entries = game_score_repo.get_leaderboard(game_name, limit)

    # Transform to leaderboard format with rank
    leaderboard_entries = []
    for idx, entry in enumerate(entries, start=1):
        leaderboard_entries.append(
            LeaderboardEntry(
                rank=idx,
                username=entry["username"],
                score=entry["score"],
                created_at=entry["created_at"],
            )
        )

    return LeaderboardResponse(
        success=True,
        game_name=game_name,
        entries=leaderboard_entries,
        total_entries=len(entries),
    )


@router.get("/{game_name}/my-best")
async def get_user_best_score(game_name: str, username: Optional[str] = None):
    """
    Get the authenticated user's best score for a specific game.
    """
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    user = user_repo.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    best = game_score_repo.get_user_best_score(user["id"], game_name)
    if not best:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No scores submitted yet"
        )

    return {"success": True, "score": best}
