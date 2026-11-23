"""
REST endpoints for managing chat sessions: list, fetch history, rename, delete. Separate from api/ws.py (the WebSocket itself) since these are plain request/response endpoints with nothing streaming or stateful.
"""

from fastapi import APIRouter, HTTPException, Header

from api.deps import verify_user_token
from store import load_chat_history, get_user_session, update_session_title, delete_session as delete_session_data
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Chat Sessions"])


@router.get("/sessions")
async def list_sessions(user_id: str, authorization: str = Header(...)):
    """
    Get list of user's chat sessions.
    Requires Bearer token in Authorization header.
    """
    # Extract token from "Bearer <token>" or handle raw token
    try:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
        else:
            token = authorization
    except AttributeError:
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    user = await verify_user_token(token)
    if not user or user["id"] != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await get_user_session(user_id)


@router.get("/chat-history")
async def get_chat_history(
    session_id: str, user_id: str, authorization: str = Header(...)
):
    """
    Get chat history for a specific session.
    Requires Bearer token in Authorization header.
    """
    token = authorization.replace("Bearer ", "")

    user = await verify_user_token(token)
    if not user or user["id"] != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await load_chat_history(user_id, session_id)


@router.put("/sessions/{session_id}/title")
async def update_session_title_endpoint(
    session_id: str, title_data: dict, authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not title_data or "title" not in title_data:
        raise HTTPException(status_code=400, detail="Missing 'title' in request body")

    if not await update_session_title(user["id"], session_id, title_data["title"]):
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Title updated successfully"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, authorization: str = Header(...)):
    """Delete a chat session and all its messages."""
    try:
        token = authorization.replace("Bearer ", "")
        user = await verify_user_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not await delete_session_data(user["id"], session_id):
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Delete session failed")
        raise HTTPException(
            status_code=500, detail="Something went wrong. Please try again."
        )
