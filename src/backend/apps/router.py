"""
Generic Apps API router.
Placeholder for future mini-apps (calculators, utilities, etc.).
"""

from fastapi import APIRouter, Request
from typing import List, Dict, Any, Optional
from ..shared.database import app_repo, user_activity_repo, user_repo
from ..shared.schemas import AppListResponse, AppInfo
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apps", tags=["Apps"])


@router.get("/", response_model=AppListResponse)
async def list_apps():
    """
    List all available/apps.

    ## Response Example
    ```json
    {
        "success": true,
        "apps": [
            {
                "id": 1,
                "name": "tic-tac-toe",
                "route_path": "/apps/tic-tac-toe",
                "description": "Classic Tic-Tac-Toe game with AI opponent",
                "icon": "🎮",
                "is_active": true
            }
        ]
    }
    ```
    """
    apps = app_repo.get_active_apps()
    return AppListResponse(success=True, apps=[AppInfo(**app) for app in apps])


@router.get("/{app_id:int}")
async def get_app_details(app_id: int):
    """
    Get details for a specific app.

    Returns app info including route and configuration.
    """
    app = app_repo.get_by_id(app_id)
    if not app or not app.get("is_active"):
        from fastapi import HTTPException
        from fastapi import status as fastapi_status

        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="App not found or inactive",
        )

    return {"success": True, "app": app}


@router.post("/{app_id:int}/launch")
async def launch_app(app_id: int, request: Request, session_id: Optional[str] = None):
    """
    Track app launch activity.

    Use this when a user opens an app to log their session.
    """
    # Get user identifier (from session or future token)
    username = request.headers.get("X-Username") or request.query_params.get("username")
    if not username:
        from fastapi import HTTPException
        from fastapi import status as fastapi_status

        raise HTTPException(
            status_code=fastapi_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Get user
    user = user_repo.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Log activity
    try:
        activity_id = user_activity_repo.log_activity(
            user_id=user["id"],
            app_id=app_id,
            session_id=session_id,
            metadata={"started_at": "now"},
        )
        logger.info(f"User {username} launched app {app_id} (session: {session_id})")
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        # Don't fail the request - logging is best effort

    return {"success": True, "session_id": session_id, "message": "App launch recorded"}
